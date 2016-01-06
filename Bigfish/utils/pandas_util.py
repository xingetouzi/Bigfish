import Bigfish.utils.algos as bf_algos
import pandas.algos as pd_algos
import numpy as np
from pandas.stats.moments import _conv_timerule, _process_data_structure, _center_window, _use_window


def _rolling_moment_2d(arg, window, func, minp, axis=0, freq=None, center=False,
                       how=None, args=(), kwargs={}, **kwds):
    """
    Rolling statistical measure using supplied function. Designed to be
    used with passed-in Cython array-based functions.

    Parameters
    ----------
    arg :  DataFrame or numpy ndarray-like
    window : Number of observations used for calculating statistic
    func : Cython function to compute rolling statistic on raw series
    minp : int
        Minimum number of observations required to have a value
    axis : int, default 0
    freq : None or string alias / date offset object, default=None
        Frequency to conform to before computing statistic
    center : boolean, default False
        Whether the label should correspond with center of window
    how : string, default 'mean'
        Method for down- or re-sampling
    args : tuple
        Passed on to func
    kwargs : dict
        Passed on to func

    Returns
    -------
    y : type of input
    """
    arg = _conv_timerule(arg, freq, how)

    return_hook, values = _process_data_structure(arg)

    if values.ndim > 2:
        raise ValueError("values's ndim should less than 2")
    if values.size == 0:
        result = values.copy()
    else:
        # actually calculate the moment. Faster way to do this?
        offset = int((window - 1) / 2.) if center else 0
        if values.ndim == 2:
            roll_generic = bf_algos.roll_generic_2d
            additional_nans = np.array([[np.NaN] * values.shape[1]] * offset)
        else:
            roll_generic = pd_algos.roll_generic
            additional_nans = np.array([np.NaN] * offset)
        calc = lambda x: func(np.concatenate((x, additional_nans)) if center else x,
                              window, minp=minp, args=args, kwargs=kwargs, roll_generic=roll_generic,
                              **kwds)
        result = calc(values)

    if center:
        result = _center_window(result, window, axis)

    return return_hook(result)


def rolling_apply_2d(arg, window, func, min_periods=None, freq=None,
                     center=False, args=(), kwargs={}):
    """Generic moving function application.

    Parameters
    ----------
    arg : Series, DataFrame
    window : int
        Size of the moving window. This is the number of observations used for
        calculating the statistic.
    func : function
        Must produce a single value from an ndarray input
    min_periods : int, default None
        Minimum number of observations in window required to have a value
        (otherwise result is NA).
    freq : string or DateOffset object, optional (default None)
        Frequency to conform the data to before computing the statistic. Specified
        as a frequency string or DateOffset object.
    center : boolean, default False
        Whether the label should correspond with center of window
    args : tuple
        Passed on to func
    kwargs : dict
        Passed on to func

    Returns
    -------
    y : type of input argument

    Notes
    -----
    By default, the result is set to the right edge of the window. This can be
    changed to the center of the window by setting ``center=True``.

    The `freq` keyword is used to conform time series data to a specified
    frequency by resampling the data. This is done with the default parameters
    of :meth:`~pandas.Series.resample` (i.e. using the `mean`).
    """
    offset = int((window - 1) / 2.) if center else 0

    def call_cython(arg, window, minp, args, kwargs, roll_generic):
        minp = _use_window(minp, window)
        return roll_generic(arg, window, minp, offset, func, args, kwargs)

    return _rolling_moment_2d(arg, window, call_cython, min_periods, freq=freq,
                              center=False, args=args, kwargs=kwargs)
