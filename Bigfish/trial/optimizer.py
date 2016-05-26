from Bigfish.app.backtest import Backtesting
import pandas as pd
import numpy as np


class Optimizer(Backtesting):
    @staticmethod
    def get_optimize_goals():
        return {'net_profit': '净利'}

    @staticmethod
    def get_optimize_types():
        return {'enumerate': '枚举', 'genetic': '遗传'}

    def get_parameters(self):
        if self.__strategy_parameters is None:
            temp = self.__strategy.get_parameters()
            for handle_name in temp.keys():
                for para_name, values in temp[handle_name].items():
                    temp[handle_name][para_name] = {'default': values, 'type': str(type(values))}
            self.__strategy_parameters = temp
        return self.__strategy_parameters

    def _enumerate_optimize(self, ranges, goal, num):
        stack = []
        range_length = []
        parameters = {}
        result = []
        head_index = []

        def get_range(range_info):
            return np.arange(range_info['start'], range_info['end'] + range_info['step'], range_info['step'])

        for handle, paras in ranges.items():
            parameters[handle] = {}
            for para, value in paras.items():
                range_value = get_range(value)
                stack.append({'handle': handle, 'para': para, 'range': range_value})
                head_index.append('%s(%s)' % (para, handle))
                range_length.append(len(range_value))
        n = len(stack)
        index = [-1] * n
        head = [0] * n

        def set_paras(n, handle=None, para=None, range=None):
            nonlocal parameters, head, index
            parameters[handle][para] = head[n] = range[index[n]]

        i = 0
        finished = False
        while 1:
            index[i] += 1
            while index[i] >= range_length[i]:
                if i == 0:
                    finished = True
                    break
                index[i] = -1
                i -= 1
                index[i] += 1
            if finished:
                break
            set_paras(i, **stack[i])
            if i == n - 1:
                performance_manager = self.start(parameters, refresh=False)
                head = pd.Series(head, index=head_index)
                optimize_info = performance_manager.get_performance().optimize_info.copy()
                target = optimize_info[goal]
                del optimize_info[goal]
                result.append(pd.concat([head, pd.Series([target], index=[goal]), optimize_info]))
            else:
                i += 1
        self.__data_generator.stop()  # 释放数据资源
        output = pd.DataFrame(result).sort_values(goal, ascending=False)
        result.clear()  # 释放资源
        output.index.name = '_'
        output = output.iloc[:num]
        return output

    def _genetic_optimize(self, ranges, goal):
        pass

    def optimize(self, ranges, type, goal, num=50):
        if not ranges:
            return
        if type is None:
            type = "enumerate"
        # TODO 不要使用硬编码
        if goal is None:
            goal = "净利($)"
        goal = "净利($)"
        optimizer = getattr(self, '_%s_optimize' % type)
        return optimizer(ranges, goal, num)
