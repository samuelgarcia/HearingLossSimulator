import numpy as np

def assert_arrays_equal(a, b, dtype=False):
    '''
    Check if two arrays have the same shape and contents.

    If dtype is True (default=False), then also theck that they have the same
    dtype.
    '''
    assert isinstance(a, np.ndarray), "a is a %s" % type(a)
    assert isinstance(b, np.ndarray), "b is a %s" % type(b)
    assert a.shape == b.shape, "%s != %s" % (a, b)
    #assert a.dtype == b.dtype, "%s and %s not same dtype %s %s" % (a, b,
    #                                                               a.dtype,
    #                                                               b.dtype)
    try:
        assert (a.flatten() == b.flatten()).all(), "%s != %s" % (a, b)
    except (AttributeError, ValueError):
        try:
            ar = np.array(a)
            br = np.array(b)
            assert (ar.flatten() == br.flatten()).all(), "%s != %s" % (ar, br)
        except (AttributeError, ValueError):
            assert np.all(a.flatten() == b.flatten()), "%s != %s" % (a, b)

    if dtype:
        assert a.dtype == b.dtype, \
            "%s and %s not same dtype %s and %s" % (a, b, a.dtype, b.dtype)
