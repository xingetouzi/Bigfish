# -*- coding: utf-8 -*-
"""
Created on Wed Nov  4 11:58:21 2015

@author: BurdenBear
"""
import ast
import os
import codecs

from Bigfish.store.code_manage import get_sys_func_list, get_sys_func_dir
from Bigfish.config import MODULES_IMPORT
from Bigfish.models.base import TradingCommands


class LocationPatcher(ast.NodeTransformer):
    def __init__(self, node):
        assert isinstance(node, ast.AST)
        assert hasattr(node, 'lineno')
        assert hasattr(node, 'col_offset')
        self.__benchmark = node

    def visit(self, node):
        method = 'visit_' + node.__class__.__name__
        visitor = getattr(self, method, self.generic_visit)
        return ast.copy_location(visitor(node), self.__benchmark)


class FunctionsDetector(ast.NodeVisitor):
    def __init__(self, funcs):
        self._funcs = funcs
        self._funcs_in_use = {}
        self._handler = None

    def visit_FunctionDef(self, node):
        if self._handler is None:
            self._handler = node.name
            self.generic_visit(node)
            self._handler = None
        else:
            self.generic_visit(node)

    def get_funcs_in_use(self):
        return self._funcs_in_use


class SystemFunctionsDetector(FunctionsDetector):
    def __init__(self):
        super(SystemFunctionsDetector, self).__init__(get_sys_func_list())
        self._sys_func_dir = get_sys_func_dir()

    def visit_Name(self, node):
        name = node.id
        if name in self._funcs and isinstance(node.ctx, ast.Load):
            if self._handler is not None:
                if name not in self._funcs_in_use:
                    self._funcs_in_use[name] = set()
                self._funcs_in_use[name].add(self._handler)
            else:
                raise RuntimeError('系统函数只能在handler中调用')
            with codecs.open(os.path.join(self._sys_func_dir, name + '.py'), 'r', "utf-8") as f:
                self.visit(ast.parse(f.read()))
                f.close()
        self.generic_visit(node)


class LocalsInjector(ast.NodeVisitor):
    """向函数中注入局部变量，参考ast.NodeVisitor"""

    def __init__(self, to_inject_init={}, to_inject_loop={}, is_signal=True):
        self.__depth = 0
        self.__to_inject_init = to_inject_init
        self.__to_inject_loop = to_inject_loop
        self.__is_signal = True

    def visit(self, node):
        self.__depth += 1
        method = 'visit_' + node.__class__.__name__
        visitor = getattr(self, method, self.generic_visit)
        visitor(node)
        self.__depth -= 1

    def visit_FunctionDef(self, node):
        self.generic_visit(node)
        if (self.__depth == 2) and (node.name in self.__to_inject_init):
            # 注入变量
            code_init = '\n'.join(self.__to_inject_init[node.name])
            location_patcher = LocationPatcher(node)
            code_init_ast = location_patcher.visit(ast.parse(code_init))
            code_loop = '\n'.join(self.__to_inject_loop[node.name])  # 每个信号或函数注入的语句可能都相同
            code_loop_ast = location_patcher.visit(ast.parse(code_loop))

            while_node = ast.copy_location(ast.While(
                body=code_loop_ast.body + node.body,
                test=ast.copy_location(ast.NameConstant(value=True), node), orelse=[]), node)
            node.body = code_init_ast.body + [self.return_to_yield(while_node)]
            # 改变函数签名
            node.args.kwonlyargs.append(location_patcher.visit(ast.arg(arg='series_id', annotation=None)))
            node.args.kw_defaults.append(location_patcher.visit(ast.Str(s='')))
            # print(ast.dump(node))

    @staticmethod
    def return_to_yield(node):

        def trans(return_node):
            if return_node:
                return [ast.Expr(value=ast.Yield(value=return_node.value)), ast.Continue()]
            else:
                return [ast.Expr(value=ast.Yield(value=None)), ast.Continue()]

        return ReturnTransformer(target=trans, add=True).trans(node)


class SeriesExporter(ast.NodeTransformer):
    """
    将形如"export[n](a,b,c)"的ast.Expr转化为形如"a,b,c=export('a','b','c',maxlen=n,series_id=id)"的语法树节点,
    id由语句在代码中的位置唯一决定
    """

    def __init__(self):
        self.__export_id = 0

    def visit_Expr(self, node):

        def get_arg_name(node):
            assert isinstance(node, ast.Name)
            assert isinstance(node.ctx, ast.Load)
            return node.id

        node = self.generic_visit(node)
        value = node.value
        if isinstance(value, ast.Call):
            if isinstance(value.func, ast.Name) and (value.func.id == 'Export') and isinstance(value.func.ctx,
                                                                                               ast.Load):
                if value.keywords:
                    # TODO 自定义错误
                    raise ValueError
                arg_names = [get_arg_name(arg_node) for arg_node in value.args]
                if not arg_names:
                    return node
                value.args[:] = [ast.copy_location(ast.Str(s=name), arg_node) for name, arg_node in
                                 zip(arg_names, value.args)]
                self.__export_id += 1
                patcher = LocationPatcher(value.args[-1])
                value.keywords.append(
                    patcher.visit(ast.keyword(arg='series_id', value=ast.Name(id='series_id', ctx=ast.Load()))))
                value.keywords.append(patcher.visit(ast.keyword(arg='export_id', value=ast.Num(n=self.__export_id))))
                value.keywords.append(
                    patcher.visit(ast.keyword(arg='barnum', value=ast.Name(id='BarNum', ctx=ast.Load()))))
                # TODO行号问题
                new_node = ast.copy_location(ast.Assign(targets=[], value=value), node)
                new_node.targets.append(ast.copy_location(
                    ast.Tuple(
                        elts=[ast.copy_location(ast.Name(id=name, ctx=ast.Store()), node) for name in
                              arg_names],
                        ctx=ast.Store()), node))
                return new_node
        return node

    def generic_visit(self, node):
        for field, old_value in ast.iter_fields(node):
            old_value = getattr(node, field, None)
            if isinstance(old_value, list):
                new_values = []
                for value in old_value:
                    if isinstance(value, ast.AST):
                        value = self.visit(value)
                        if value is None:
                            continue
                        elif not isinstance(value, ast.AST):
                            new_values.extend(value)
                            continue
                    new_values.append(value)
                old_value[:] = new_values
            elif isinstance(old_value, ast.AST):
                new_node = self.visit(old_value)
                if new_node is None:
                    delattr(node, field)
                elif not isinstance(new_node, ast.AST):
                    new_node_tuple = ast.copy_location(ast.Tuple(elts=list(new_node), ctx=ast.load()), new_node[0])
                    setattr(node, field, new_node_tuple)
                else:
                    setattr(node, field, new_node)
        return node


class ImportInspector(ast.NodeVisitor):
    """
    对import进行限制性检查。
    """
    __MODULES_IMPORT = MODULES_IMPORT

    @staticmethod
    def raise_error(name):
        raise ImportError('<%s>模块不在Bigfish平台可导入模块列表中' % name)

    def visit_Import(self, node):
        for children in node.names:
            name = children.name.split('.')[0]
            if name not in self.__MODULES_IMPORT:
                self.raise_error(name)

    def visit_ImportFrom(self, node):
        if node.level:
            raise SystemError("不支持相对导入")
        name = node.module.split('.')[0]
        if name not in self.__MODULES_IMPORT:
            self.raise_error(name)


class InitTransformer(ast.NodeVisitor):
    def __init__(self):
        self.__depth = 0
        self.__in_init = False
        self.init_node = None

    def visit(self, node):
        self.__depth += 1
        in_init_ = self.__in_init
        method = 'visit_' + node.__class__.__name__
        visitor = getattr(self, method, self.generic_visit)
        visitor(node)
        self.__depth -= 1
        self.__in_init = in_init_

    def visit_Yield(self, node):
        self.generic_visit(node)
        if self.__in_init:
            raise SyntaxError("'yield'不应出现在init函数中")

    @staticmethod
    def trans(node):
        result = ast.parse('return locals()').body[0]
        if node:
            LocationPatcher(node).visit(result)
        return result

    def visit_FunctionDef(self, node):
        if self.__depth == 2 and node.name == 'init':
            self.__in_init = True
            self.init_node = ReturnTransformer(target=self.trans, add=True).trans(node)
        self.generic_visit(node)


class ReturnTransformer(ast.NodeTransformer):
    def __init__(self, target=None, add=True):
        """
        Return节点修改器，将一个含有body属性的节点的AST子树中所有的Return节点修改为Target的返回值
        如果没有发现Return节点，且add为True，则在body中加入Target的返回值
        """
        self.__in_func_def = False  # 用于处理是否在嵌套定义的函数当中
        self.__target = target
        self.__add = add
        self.__has_return = False

    def visit_Return(self, node):
        if not self.__in_func_def:
            self.__has_return = True
            return self.patch(node, self.__target(node))
        else:
            return node

    def visit_FunctionDef(self, node):
        old = self.__in_func_def
        self.__in_func_def = True
        result = self.generic_visit(node)
        self.__in_func_def = old
        return result

    @staticmethod
    def patch(bench, node):
        patcher = LocationPatcher(bench)
        if isinstance(node, list):
            return list(map(lambda x: patcher.visit(x), node))
        else:
            return patcher.visit(node)

    def trans(self, node):
        self.__has_return = False
        node = self.visit(node)
        if (not self.__has_return) and self.__add:
            to_add = self.patch(node.body[-1], self.__target(None))
            if isinstance(to_add, list):
                node.body.extend(to_add)
            else:
                node.body.append(to_add)
        return node


def wrap_with_module(nodes):
    try:
        return ast.Module(body=list(nodes))
    except TypeError:
        return ast.Module(body=[nodes])
    except Exception as e:
        raise e


class TradingCommandsTransformer(ast.NodeTransformer):
    def visit_Call(self, node):
        if isinstance(node.func, ast.Name) and isinstance(node.func.ctx, ast.Load):
            if node.func.id in map(lambda x: x.value, list(TradingCommands)):
                parser = LocationPatcher(node)
                node.keywords.append(parser.visit(ast.keyword(arg='lineno', value=ast.Num(n=node.lineno))))
                node.keywords.append(parser.visit(ast.keyword(arg='col_offset', value=ast.Num(n=node.col_offset))))
        return node
