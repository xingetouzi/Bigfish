# -*- coding: utf-8 -*-
"""
Created on Wed Nov  4 11:58:21 2015

@author: BurdenBear
"""
import ast
import bigfish_functions


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


class LocalsInjector(ast.NodeVisitor):
    """向函数中注入局部变量，参考ast.NodeVisitor"""

    def __init__(self, to_inject={}):
        self.__depth = 0
        self.__to_inject = to_inject

    def visit(self, node):
        self.__depth += 1
        method = 'visit_' + node.__class__.__name__
        visitor = getattr(self, method, self.generic_visit)
        visitor(node)
        self.__depth -= 1

    def visit_FunctionDef(self, node):
        self.generic_visit(node)
        if (self.__depth == 2) and (node.name in self.__to_inject):
            code = '\n'.join(['from bigfish_functions import {0} as {0}'.format(func)
                              for func in bigfish_functions.__all__]) + '\n'
            code += '\n'.join(self.__to_inject[node.name])
            code += '\nbarnum = 0\n'
            location_patcher = LocationPatcher(node)
            code_ast = location_patcher.visit(ast.parse(code))
            barnum_ast = location_patcher.visit(ast.parse('barnum += 1'))
            while_node = ast.copy_location(ast.While(
                    body=barnum_ast.body + node.body + [
                        LocationPatcher(node.body[-1]).visit(ast.Expr(value=ast.Yield(value=None)))],
                    test=ast.copy_location(ast.NameConstant(value=True), node), orelse=[]), node)
            node.body = code_ast.body + [while_node]
            # print(ast.dump(node))


class SeriesExporter(ast.NodeTransformer):
    """
    将形如"export[n](a,b,c)"的ast.Expr转化为形如"a,b,c=export('a','b','c',maxlen=n,series_id=id)"的语法树节点,
    id由语句在代码中的位置唯一决定
    """

    def __init__(self, file):
        self.__count = 0
        self.__series_id = file

    def visit_Expr(self, node):

        def get_arg_name(node):
            assert isinstance(node, ast.Name)
            assert isinstance(node.ctx, ast.Load)
            return node.id

        node = self.generic_visit(node)
        value = node.value
        if isinstance(value, ast.Call):
            if isinstance(value.func, ast.Name) and (value.func.id == 'export') and isinstance(value.func.ctx,
                                                                                               ast.Load):
                if value.keywords:
                    # TODO 自定义错误
                    raise ValueError
                arg_names = [get_arg_name(arg_node) for arg_node in value.args]
                if not arg_names:
                    return node
                value.args[:] = [ast.copy_location(ast.Str(s=name), arg_node) for name, arg_node in
                                 zip(arg_names, value.args)]
                self.__count += 1
                value.keywords.append(ast.copy_location(
                        ast.keyword(arg='series_id',
                                    value=ast.copy_location(ast.Str(s=self.__series_id+self.__count), value.args[-1])),
                        value.args[-1]))
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
