# -*- coding: utf-8 -*-
import warnings

from attest import Tests, assert_hook, raises
try:
    import numpy
except ImportError:
    numpy = False

import trueskill
from trueskill import *


suite = Tests()


# usage


@suite.test
def compatibility_with_another_rating_systems():
    """All rating system modules should implement ``rate_1vs1`` and
    ``quality_1vs1`` to provide shortcuts for 1 vs 1 simple competition games.
    """
    r1, r2 = Rating(30, 3), Rating(20, 2)
    assert quality_1vs1(r1, r2) == quality([(r1,), (r2,)])
    rated = rate([(r1,), (r2,)])
    assert rate_1vs1(r1, r2) == (rated[0][0], rated[1][0])
    rated = rate([(r1,), (r2,)], [0, 0])
    assert rate_1vs1(r1, r2, drawn=True) == (rated[0][0], rated[1][0])


@suite.test
def compare_ratings():
    assert Rating(1, 2) == Rating(1, 2)
    assert Rating(1, 2) != Rating(1, 3)
    assert Rating(2, 2) > Rating(1, 2)
    assert Rating(3, 2) >= Rating(1, 2)
    assert Rating(0, 2) < Rating(1, 2)
    assert Rating(-1, 2) <= Rating(1, 2)


@suite.test
def rating_to_number():
    assert int(Rating(1, 2)) == 1
    assert long(Rating(1, 2)) == 1L
    assert float(Rating(1.1, 2)) == 1.1
    assert complex(Rating(1.2, 2)) == 1.2+0j


@suite.test
def unsorted_groups():
    t1, t2, t3 = generate_teams([1, 1, 1])
    rated = rate([t1, t2, t3], [2, 1, 0])
    assert almost(rated) == \
           [(18.325, 6.656), (25.000, 6.208), (31.675, 6.656)]


@suite.test
def custom_environment():
    env = TrueSkill(draw_probability=.50)
    t1, t2 = generate_teams([1, 1], env=env)
    rated = env.rate([t1, t2])
    assert almost(rated) == [(30.267, 7.077), (19.733, 7.077)]


@suite.test
def setup_global_environment():
    try:
        setup(draw_probability=.50)
        t1, t2 = generate_teams([1, 1])
        rated = rate([t1, t2])
        assert almost(rated) == [(30.267, 7.077), (19.733, 7.077)]
    finally:
        # rollback
        setup()


@suite.test
def invalid_rating_groups():
    env = TrueSkill()
    with raises(ValueError):
        env.validate_rating_groups([])
    with raises(ValueError):
        env.validate_rating_groups([()])
    with raises(ValueError):
        env.validate_rating_groups([(Rating(),)])
    with raises(ValueError):
        env.validate_rating_groups([(Rating(),), ()])
    with raises(TypeError):
        env.validate_rating_groups([(Rating(),), {0: Rating()}])


@suite.test
def deprecated_methods():
    env = TrueSkill()
    r1, r2, r3 = Rating(), Rating(), Rating()
    try:
        # clear warning registry to catch all warnings explicitly
        trueskill.__warningregistry__.clear()
    except AttributeError:
        pass
    with warnings.catch_warnings(record=True) as w:
        warnings.simplefilter('always')
        transform_ratings([(r1,), (r2,), (r3,)])
        match_quality([(r1,), (r2,), (r3,)])
        env.transform_ratings([(r1,), (r2,), (r3,)])
        env.match_quality([(r1,), (r2,), (r3,)])
        env.Rating()
    assert len(w) == 5
    assert w[0].category is DeprecationWarning
    assert w[1].category is DeprecationWarning
    assert w[2].category is DeprecationWarning
    assert w[3].category is DeprecationWarning
    assert w[4].category is DeprecationWarning


@suite.test
def deprecated_individual_rating_groups():
    r1, r2, r3 = Rating(50, 1), Rating(10, 5), Rating(15, 5)
    with raises(TypeError):
        rate([r1, r2, r3])
    with raises(TypeError):
        quality([r1, r2, r3])
    # deprecated methods accept individual rating groups
    with warnings.catch_warnings():
        warnings.simplefilter('ignore')
        assert transform_ratings([r1, r2, r3]) == rate([(r1,), (r2,), (r3,)])
        assert match_quality([r1, r2, r3]) == quality([(r1,), (r2,), (r3,)])


@suite.test
def rating_tuples():
    r1, r2, r3 = Rating(), Rating(), Rating()
    rated = rate([(r1, r2), (r3,)])
    assert len(rated) == 2
    assert isinstance(rated[0], tuple)
    assert isinstance(rated[1], tuple)
    assert len(rated[0]) == 2
    assert len(rated[1]) == 1
    assert isinstance(rated[0][0], Rating)


@suite.test
def rating_dicts():
    class Player(object):
        def __init__(self, name, rating, team):
            self.name = name
            self.rating = rating
            self.team = team
    p1 = Player('Player A', Rating(), 0)
    p2 = Player('Player B', Rating(), 0)
    p3 = Player('Player C', Rating(), 1)
    rated = rate([{p1: p1.rating, p2: p2.rating}, {p3: p3.rating}])
    assert len(rated) == 2
    assert isinstance(rated[0], dict)
    assert isinstance(rated[1], dict)
    assert len(rated[0]) == 2
    assert len(rated[1]) == 1
    assert p1 in rated[0]
    assert p2 in rated[0]
    assert p3 in rated[1]
    assert p1 not in rated[1]
    assert p2 not in rated[1]
    assert p3 not in rated[0]
    assert isinstance(rated[0][p1], Rating)
    p1.rating = rated[p1.team][p1]
    p2.rating = rated[p2.team][p2]
    p3.rating = rated[p3.team][p3]


# algorithm


def generate_teams(sizes, env=None):
    rating_cls = Rating if env is None else env.create_rating
    rating_groups = []
    for size in sizes:
        ratings = []
        for x in xrange(size):
            ratings.append(rating_cls())
        rating_groups.append(tuple(ratings))
    return rating_groups


def generate_individual(size, env=None):
    return generate_teams([1] * size, env)


class almost(object):

    def __init__(self, val, precision=3):
        if isinstance(val, list):
            flatten = []
            for item in val:
                if isinstance(item, dict):
                    item = tuple(item.itervalues())
                if isinstance(item, tuple):
                    for rating in item:
                        flatten.append(tuple(rating))
            self.val = flatten
        else:
            self.val = val
        self.precision = precision

    def almost_equals(self, val1, val2):
        if isinstance(val1, list):
            for item1, item2 in zip(val1, val2):
                if not self.almost_equals(item1[0], item2[0]) or \
                   not self.almost_equals(item1[1], item2[1]):
                    return False
            return True
        else:
            if round(val1, self.precision) == round(val2, self.precision):
                return True
            fmt = '%.{0}f'.format(self.precision)
            mantissa = lambda f: int((fmt % f).replace('.', ''))
            return abs(mantissa(val1) - mantissa(val2)) <= 1

    def __eq__(self, other):
        return self.almost_equals(self.val, other)

    def __repr__(self):
        return repr(self.val)


@suite.test
def n_vs_n():
    # 1 vs 1
    t1, t2 = generate_teams([1, 1])
    assert almost(quality([t1, t2])) == 0.447
    assert almost(rate([t1, t2])) == \
           [(29.396, 7.171), (20.604, 7.171)]
    assert almost(rate([t1, t2], [0, 0])) == \
           [(25.000, 6.458), (25.000, 6.458)]
    # 2 vs 2
    t1, t2 = generate_teams([2, 2])
    assert almost(quality([t1, t2])) == 0.447
    assert almost(rate([t1, t2])) == \
           [(28.108, 7.774), (28.108, 7.774), (21.892, 7.774), (21.892, 7.774)]
    assert almost(rate([t1, t2], [0, 0])) == \
           [(25.000, 7.455), (25.000, 7.455), (25.000, 7.455), (25.000, 7.455)]
    # 4 vs 4
    t1, t2 = generate_teams([4, 4])
    assert almost(quality([t1, t2])) == 0.447
    assert almost(rate([t1, t2])) == \
           [(27.198, 8.059), (27.198, 8.059), (27.198, 8.059), (27.198, 8.059),
            (22.802, 8.059), (22.802, 8.059), (22.802, 8.059), (22.802, 8.059)]


@suite.test
def one_vs_n():
    t1, = generate_teams([1])
    # 1 vs 2
    t2, = generate_teams([2])
    assert almost(quality([t1, t2])) == 0.135
    assert almost(rate([t1, t2])) == \
           [(33.730, 7.317), (16.270, 7.317), (16.270, 7.317)]
    assert almost(rate([t1, t2], [0, 0])) == \
           [(31.660, 7.138), (18.340, 7.138), (18.340, 7.138)]
    # 1 vs 3
    t2, = generate_teams([3])
    assert almost(quality([t1, t2])) == 0.012
    assert almost(rate([t1, t2])) == \
           [(36.337, 7.527), (13.663, 7.527), (13.663, 7.527), (13.663, 7.527)]
    assert almost(rate([t1, t2], [0, 0]), 2) == \
           [(34.990, 7.455), (15.010, 7.455), (15.010, 7.455), (15.010, 7.455)]
    # 1 vs 7
    t2, = generate_teams([7])
    assert almost(quality([t1, t2])) == 0
    assert almost(rate([t1, t2])) == \
           [(40.582, 7.917), (9.418, 7.917), (9.418, 7.917), (9.418, 7.917),
            (9.418, 7.917), (9.418, 7.917), (9.418, 7.917), (9.418, 7.917)]


@suite.test
def individual():
    # 3 players
    players = generate_individual(3)
    assert almost(quality(players)) == 0.200
    assert almost(rate(players)) == \
           [(31.675, 6.656), (25.000, 6.208), (18.325, 6.656)]
    assert almost(rate(players, [0] * 3)) == \
           [(25.000, 5.698), (25.000, 5.695), (25.000, 5.698)]
    # 4 players
    players = generate_individual(4)
    assert almost(quality(players)) == 0.089
    assert almost(rate(players)) == \
           [(33.207, 6.348), (27.401, 5.787), (22.599, 5.787), (16.793, 6.348)]
    # 5 players
    players = generate_individual(5)
    assert almost(quality(players)) == 0.040
    assert almost(rate(players)) == \
           [(34.363, 6.136), (29.058, 5.536), (25.000, 5.420), (20.942, 5.536),
            (15.637, 6.136)]
    # 8 players
    players = generate_individual(8)
    assert almost(quality(players)) == 0.004
    assert almost(rate(players, [0] * 8)) == \
           [(25.000, 4.592), (25.000, 4.583), (25.000, 4.576), (25.000, 4.573),
            (25.000, 4.573), (25.000, 4.576), (25.000, 4.583), (25.000, 4.592)]
    # 16 players
    players = generate_individual(16)
    assert almost(rate(players)) == \
           [(40.539, 5.276), (36.810, 4.711), (34.347, 4.524), (32.336, 4.433),
            (30.550, 4.380), (28.893, 4.349), (27.310, 4.330), (25.766, 4.322),
            (24.234, 4.322), (22.690, 4.330), (21.107, 4.349), (19.450, 4.380),
            (17.664, 4.433), (15.653, 4.524), (13.190, 4.711), (9.461, 5.276)]


@suite.test
def multiple_teams():
    # 2 vs 4 vs 2
    t1 = (Rating(40, 4), Rating(45, 3))
    t2 = (Rating(20, 7), Rating(19, 6), Rating(30, 9), Rating(10, 4))
    t3 = (Rating(50, 5), Rating(30, 2))
    assert almost(quality([t1, t2, t3])) == 0.367
    assert almost(rate([t1, t2, t3], [0, 1, 1])) == \
           [(40.877, 3.840), (45.493, 2.934), (19.609, 6.396), (18.712, 5.625),
            (29.353, 7.673), (9.872, 3.891), (48.830, 4.590), (29.813, 1.976)]


@suite.test
def upset():
    # 1 vs 1
    t1, t2 = (Rating(),), (Rating(50, 12.5),)
    assert almost(quality([t1, t2])) == 0.110
    assert almost(rate([t1, t2], [0, 0])) == [(31.662, 7.137), (35.010, 7.910)]
    # 2 vs 2
    t1 = (Rating(20, 8), Rating(25, 6))
    t2 = (Rating(35, 7), Rating(40, 5))
    assert almost(quality([t1, t2])) == 0.084
    assert almost(rate([t1, t2])) == \
           [(29.698, 7.008), (30.455, 5.594), (27.575, 6.346), (36.211, 4.768)]
    # 3 vs 2
    t1 = (Rating(28, 7), Rating(27, 6), Rating(26, 5))
    t2 = (Rating(30, 4), Rating(31, 3))
    assert almost(quality([t1, t2])) == 0.254
    assert almost(rate([t1, t2], [0, 1])) == \
           [(28.658, 6.770), (27.484, 5.856), (26.336, 4.917), (29.785, 3.958),
            (30.879, 2.983)]
    assert almost(rate([t1, t2], [1, 0])) == \
           [(21.840, 6.314), (22.474, 5.575), (22.857, 4.757), (32.012, 3.877),
            (32.132, 2.949)]
    # 8 players
    players = [(Rating(10, 8),), (Rating(15, 7),), (Rating(20, 6),),
               (Rating(25, 5),), (Rating(30, 4),), (Rating(35, 3),),
               (Rating(40, 2),), (Rating(45, 1),)]
    assert almost(quality(players)) == 0.000
    assert almost(rate(players)) == \
           [(35.135, 4.506), (32.585, 4.037), (31.329, 3.756), (30.984, 3.453),
            (31.751, 3.064), (34.051, 2.541), (38.263, 1.849), (44.118, 0.983)]


# reported bugs


@suite.test
def issue3():
    """The `issue #3`_, opened by @youknowone.
    
    These inputs led to ZeroDivisionError before 0.1.4. Also another TrueSkill
    implementations cannot calculate this case.

    .. _issue #3: https://github.com/sublee/trueskill/issues/3
    """
    # @konikos's case 1
    t1 = (Rating(42.234, 3.728), Rating(43.290, 3.842))
    t2 = (Rating(16.667, 0.500), Rating(16.667, 0.500), Rating(16.667, 0.500),
          Rating(16.667, 0.500), Rating(16.667, 0.500), Rating(16.667, 0.500),
          Rating(16.667, 0.500), Rating(16.667, 0.500), Rating(16.667, 0.500),
          Rating(16.667, 0.500), Rating(16.667, 0.500), Rating(16.667, 0.500),
          Rating(16.667, 0.500), Rating(16.667, 0.500), Rating(16.667, 0.500))
    rate([t1, t2], [6, 5])
    # @konikos's case 2
    t1 = (Rating(25.000, 0.500), Rating(25.000, 0.500), Rating(25.000, 0.500),
          Rating(25.000, 0.500), Rating(33.333, 0.500), Rating(33.333, 0.500),
          Rating(33.333, 0.500), Rating(33.333, 0.500), Rating(41.667, 0.500),
          Rating(41.667, 0.500), Rating(41.667, 0.500), Rating(41.667, 0.500))
    t2 = (Rating(42.234, 3.728), Rating(43.291, 3.842))
    rate([t1, t2], [0, 28])



@suite.test_if(numpy)
def issue4():
    """The `issue #4`_, opened by @sublee.

    numpy.float64 handles floating-point error by different way. For example,
    it can just warn RuntimeWarning on n/0 problem instead of throwing
    ZeroDivisionError.

    .. _issue #4: https://github.com/sublee/trueskill/issues/4
    """
    r1, r2 = Rating(105.247, 0.439), Rating(27.030, 0.901)
    # make numpy to raise FloatingPointError instead of warning RuntimeWarning
    old_settings = numpy.seterr(divide='raise')
    try:
        rate([(r1,), (r2,)])
    finally:
        numpy.seterr(**old_settings)
