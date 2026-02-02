"""
Analyze co-occurrence patterns from simulation results.

This script helps answer the question: "Which hens frequently visit nests together?"
"""

import json
from pathlib import Path
from typing import Dict, List, Tuple
from collections import defaultdict
import argparse


def load_co_occurrences(file_path: Path) -> Dict[str, int]:
    """Load co-occurrence data from JSON file."""
    with file_path.open('r') as f:
        return json.load(f)


def find_most_frequent_pairs(
    co_occurrences: Dict[str, int], top_n: int = 20
) -> List[Tuple[str, str, int]]:
    """Find the pairs of hens that most frequently visit nests together.
    
    Returns:
        List of tuples (hen_a, hen_b, count) sorted by count descending
    """
    pairs = []
    for pair_str, count in co_occurrences.items():
        hen_a, hen_b = pair_str.split(',')
        pairs.append((hen_a, hen_b, count))
    
    return sorted(pairs, key=lambda x: x[2], reverse=True)[:top_n]


def find_hen_companions(
    co_occurrences: Dict[str, int], hen_id: int, top_n: int = 10
) -> List[Tuple[int, int]]:
    """Find which hens most frequently accompany a specific hen.
    
    Args:
        co_occurrences: Co-occurrence data
        hen_id: The hen to analyze
        top_n: Number of top companions to return
    
    Returns:
        List of tuples (companion_hen_id, count) sorted by count descending
    """
    companions = []
    hen_id_str = str(hen_id)
    
    for pair_str, count in co_occurrences.items():
        hen_a, hen_b = pair_str.split(',')
        
        if hen_a == hen_id_str:
            companions.append((int(hen_b), count))
        elif hen_b == hen_id_str:
            companions.append((int(hen_a), count))
    
    return sorted(companions, key=lambda x: x[1], reverse=True)[:top_n]


def analyze_social_network(
    co_occurrences: Dict[str, int], min_co_occurrences: int = 3
) -> Dict[int, List[int]]:
    """Build a social network of hens based on frequent co-occurrences.
    
    Args:
        co_occurrences: Co-occurrence data
        min_co_occurrences: Minimum co-occurrences to consider a connection
    
    Returns:
        Dict mapping hen_id -> list of connected hen_ids
    """
    network = defaultdict(list)
    
    for pair_str, count in co_occurrences.items():
        if count >= min_co_occurrences:
            hen_a, hen_b = map(int, pair_str.split(','))
            network[hen_a].append(hen_b)
            network[hen_b].append(hen_a)
    
    return dict(network)


def print_report(simulation_name: str, data_dir: Path) -> None:
    """Print a comprehensive co-occurrence analysis report."""
    co_occ_file = data_dir / simulation_name / "co_occurrences.json"
    
    if not co_occ_file.exists():
        print(f"Error: {co_occ_file} not found")
        return
    
    co_occurrences = load_co_occurrences(co_occ_file)
    
    print("=" * 80)
    print(f"CO-OCCURRENCE ANALYSIS: {simulation_name}")
    print("=" * 80)
    print(f"\nTotal unique pairs tracked: {len(co_occurrences)}")
    
    # Statistics
    counts = list(co_occurrences.values())
    if counts:
        print(f"Average co-occurrences per pair: {sum(counts) / len(counts):.2f}")
        print(f"Maximum co-occurrences: {max(counts)}")
        print(f"Minimum co-occurrences: {min(counts)}")
    
    # Most frequent pairs
    print("\n" + "-" * 80)
    print("TOP 20 PAIRS THAT MOST FREQUENTLY VISIT NESTS TOGETHER")
    print("-" * 80)
    
    top_pairs = find_most_frequent_pairs(co_occurrences, top_n=20)
    for rank, (hen_a, hen_b, count) in enumerate(top_pairs, 1):
        print(f"{rank:2d}. Hen {hen_a:>4s} & Hen {hen_b:>4s}: {count:4d} co-occurrences")
    
    # Social network analysis
    print("\n" + "-" * 80)
    print("SOCIAL NETWORK: Hens with frequent connections (min 3 co-occurrences)")
    print("-" * 80)
    
    network = analyze_social_network(co_occurrences, min_co_occurrences=3)
    if network:
        # Sort by number of connections
        sorted_hens = sorted(network.items(), key=lambda x: len(x[1]), reverse=True)
        
        print(f"\nTotal hens with strong connections: {len(network)}")
        print(f"\nTop 10 most socially connected hens:")
        for rank, (hen_id, companions) in enumerate(sorted_hens[:10], 1):
            print(f"{rank:2d}. Hen {hen_id:4d}: connected to {len(companions)} other hens")
            # Show companions
            companion_str = ", ".join(str(c) for c in sorted(companions)[:5])
            if len(companions) > 5:
                companion_str += f", ... (+{len(companions) - 5} more)"
            print(f"    Companions: {companion_str}")
    else:
        print("No strong social connections found (all pairs have <3 co-occurrences)")
    
    print("\n" + "=" * 80)


def main():
    parser = argparse.ArgumentParser(
        description="Analyze hen co-occurrence patterns from simulation data"
    )
    parser.add_argument(
        "--data-dir",
        type=Path,
        default=Path("data"),
        help="Base directory containing simulation results"
    )
    parser.add_argument(
        "--simulation",
        type=str,
        default="pre_1",
        help="Simulation name to analyze (e.g., 'pre_1', 'post_1')"
    )
    parser.add_argument(
        "--hen-id",
        type=int,
        help="Analyze companions of a specific hen"
    )
    
    args = parser.parse_args()
    
    if args.hen_id:
        # Specific hen analysis
        co_occ_file = args.data_dir / args.simulation / "co_occurrences.json"
        co_occurrences = load_co_occurrences(co_occ_file)
        
        companions = find_hen_companions(co_occurrences, args.hen_id, top_n=15)
        
        print(f"\nCompanions of Hen {args.hen_id} (from {args.simulation}):")
        print("-" * 60)
        if companions:
            for rank, (companion_id, count) in enumerate(companions, 1):
                print(f"{rank:2d}. Hen {companion_id:4d}: {count:4d} co-occurrences")
        else:
            print(f"Hen {args.hen_id} has no recorded co-occurrences")
    else:
        # Full report
        print_report(args.simulation, args.data_dir)


if __name__ == "__main__":
    main()
