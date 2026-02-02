from src.stochastic.distributions import ServiceTimeSampler


def test_service_sampler_mixture_bounds():
    sampler = ServiceTimeSampler(
        {
            "day": {
                "gamma": {"shape": 1.0, "rate": 0.01},
                "uniform": {"min": 5.0, "max": 10.0},
                "mixture_prob": 0.5,
                "arrival_rate_per_second": 1.0,
            }
        }
    )

    samples = [sampler.sample("day") for _ in range(200)]
    assert all(val > 0 for val in samples)


def test_arrival_rate_accessor():
    sampler = ServiceTimeSampler(
        {"evening": {"gamma": {"shape": 1, "rate": 1}, "uniform": {"min": 1, "max": 2}, "mixture_prob": 1, "arrival_rate_per_second": 2}}
    )
    assert sampler.arrival_rate_per_second("evening") == 2
