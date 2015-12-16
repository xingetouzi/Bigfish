# -*- coding: utf-8 -*-
"""
Created on Wed Nov  4 11:58:21 2015

@author: BurdenBear
"""

import ast

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
        #print("<deep>:<%d>" % self.__depth, node)
        if self.__depth == 0:
            ast.fix_missing_locations(node)

    def visit_FunctionDef(self,node):
        self.generic_visit(node)        
        if (self.__depth == 2) and (node.name in self.__to_inject):        
            #print("function<%s> find!" % node.name)
            #print(ast.dump(node))
            code = '\n'.join(self.__to_inject[node.name])       
            code += '\nbarnum = 0\n'
            code_ast = ast.parse(code)
            barnum_ast = ast.parse('barnum += 1')
            while_node = ast.While(test=ast.NameConstant(value=True),
            body = barnum_ast.body+node.body+[ast.Expr(value=ast.Yield(value=None))],
            orelse=[])
            node.body = code_ast.body + [while_node]
            #print(ast.dump(node))