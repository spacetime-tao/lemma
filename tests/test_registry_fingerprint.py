"""Stable fingerprint for generated problem registry."""

from lemma.problems.generated import RNG_MIX_TAG, generated_registry_canonical_dict, generated_registry_sha256

_OLD_BUILDER_FNS = [
    "_b_true_easy",
    "_b_nat_add_norm_easy",
    "_b_nat_le_norm_easy",
    "_b_bool_and_easy",
    "_b_list_len_easy",
    "_b_list_reverse_len_easy",
    "_b_real_add_norm_easy",
    "_b_finset_card_easy",
    "_b_forall_le_refl_medium",
    "_b_list_reverse_length_medium",
    "_b_add_comm_nat_medium",
    "_b_mul_assoc_nat_medium",
    "_b_sq_expand_real_medium",
    "_b_implication_true_medium",
    "_b_odd_square_odd_medium",
    "_b_dvd_trans_medium",
    "_b_set_inter_subset_medium",
    "_b_sum_range_medium",
    "_b_det_unit_medium",
    "_b_metric_triangle_medium",
    "_b_continuous_id_medium",
    "_b_exists_prime_dvd_hard",
    "_b_inf_many_primes_hard",
    "_b_sqrt2_irrational_hard",
    "_b_finset_union_card_hard",
    "_b_set_inter_union_distrib_hard",
    "_b_mul_add_distrib_nat_medium",
    "_b_sq_nonneg_real_medium",
    "_b_abs_triangle_int_medium",
    "_b_finset_filter_card_le_medium",
    "_b_sum_range_succ_nat_medium",
    "_b_pow_two_mul_self_nat_hard",
    "_b_finset_insert_card_easy",
    "_b_logic_and_comm_medium",
    "_b_min_le_left_nat_medium",
    "_b_finset_subset_card_le_hard",
    "_b_finset_range_card_easy",
    "_b_list_append_length_medium",
    "_b_set_union_subset_medium",
    "_b_set_subset_antisymm_hard",
]


def test_generated_registry_sha256_stable() -> None:
    h = generated_registry_sha256()
    assert len(h) == 64
    assert generated_registry_sha256() == h


def test_generated_registry_fingerprint_covers_source_and_rng_tag() -> None:
    registry = generated_registry_canonical_dict()
    builders = registry["builders"]

    assert registry["rng_mix_tag"] == RNG_MIX_TAG
    assert registry["builder_count"] == 85
    assert registry["split_counts"] == {"easy": 10, "medium": 35, "hard": 35, "extreme": 5}
    assert registry["split_weights"] == {"easy": 10, "medium": 35, "hard": 50, "extreme": 5}
    assert len(builders) == 85
    assert all(len(builder["source_sha256"]) == 64 for builder in builders)
    assert all(builder["topic"] for builder in builders)
    assert all(builder["family"] for builder in builders)
    assert all(builder["informal_statement"] for builder in builders)
    assert [builder["fn"] for builder in builders[:40]] == _OLD_BUILDER_FNS
