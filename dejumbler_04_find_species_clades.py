#!/usr/bin/env python3

import sys
from Bio import Phylo
from pathlib import Path
import collections


def main():
    cluster_accessions = load_cluster_accessions()
    accession_species = load_accession_species()

    tree = Phylo.read('tree/tree.newick', 'newick')
    tree.root_at_midpoint()

    for clade in tree.find_clades():
        if clade.name is None:
            continue
        cluster_name = clade.name[:-7]
        accessions = cluster_accessions[cluster_name]
        species = [accession_species[a] for a in accessions]
        species_counts = collections.Counter(species)
        formatted_species_counts = []
        for species, count in sorted(species_counts.items(), key=lambda x: (1 / x[1], x[0])):
            formatted_species_counts.append(str(count) + ' x ' + species)
        formatted_species_counts = ', '.join(formatted_species_counts)
        clade.name = cluster_name + ' (' + formatted_species_counts + ')'

    cluster_accessions = load_cluster_accessions()

    all_tip_names = get_tip_names(tree.root)
    all_species_counts = get_species_counts_from_tip_names(all_tip_names)
    all_species_names = sorted(all_species_counts.keys())

    best_scores = {s: 0.0 for s in all_species_names
                   if not s.endswith(' unknown')}
    best_clades = {}

    for clade in tree.find_clades():
        tip_names = get_tip_names(clade)
        species_counts = get_species_counts_from_tip_names(tip_names)
        for species in species_counts:
            if species.endswith(' unknown'):
                continue
            score = score_clade_for_species(species, species_counts, all_species_counts)
            if score > best_scores[species]:
                best_scores[species] = score
                best_clades[species] = clade

    species_by_score = []
    for species, clade in best_clades.items():
        tip_names = get_tip_names(clade)
        cluster_names = [x.split()[0] for x in tip_names]
        score = best_scores[species]
        accessions = []
        for cluster_name in cluster_names:
            accessions += cluster_accessions[cluster_name]
        species_by_score.append((species, score, accessions, clade))
    species_by_score = sorted(species_by_score, reverse=True, key=lambda x: (x[1], len(x[2])))

    for species, score, accessions, clade in species_by_score:
        print()
        print(species)
        print('------------------------------------------------')
        print('score = ' + ('%.4f' % score))
        print(', '.join(accessions))
        print()
        if score == 1.0 and clade.name is None:
            clade.name = species
    
    Phylo.write(tree, 'tree_with_species.newick', 'newick')


def load_accession_species():
    accession_species = {}

    # Load from NCBI metadata first...
    data_files = [str(x) for x in Path.cwd().glob('assemblies/*/data.tsv')]
    for data_file in data_files:
        with open(data_file, 'rt') as data:
            for line in data:
                parts = line.split('\t')
                accession = parts[0]
                if accession == 'assembly_accession':
                    continue
                species = parts[9]
                species_parts = species.split(' ')[0:2]
                if species_parts[1] == 'sp.':
                    species_parts[1] = 'unknown'
                species = ' '.join(species_parts)
                accession_species[accession] = species

    # ...and then load from the user-defined file, so they can overwrite NCBI species.
    if Path('user-defined_accession_species').is_file():
        with open('user-defined_accession_species', 'rt') as user_species:
            for line in user_species:
                parts = line.split('\t')
                if parts[0] == 'Accession':
                    continue
                if len(parts) < 2:
                    continue
                accession, species = parts[0], parts[1]
                accession_species[accession] = species

    # If the user-defined file doesn't exist yet, make an empty one.
    else:
        with open('user-defined_accession_species', 'wt') as user_species:
            user_species.write('Accession\tSpecies\tNotes\n')

    return accession_species


def get_tip_names(clade):
    tip_names = []
    if clade.name is not None:
       tip_names.append(clade.name)
    for child in clade:
        tip_names += get_tip_names(child)
    return tip_names


def get_species_counts_from_tip_names(tip_names):
    count_texts = []
    for tip_name in tip_names:
        assert tip_name.endswith(')')
        tip_name = tip_name[:-1]
        tip_name = tip_name.split(' (')[1]
        count_texts += tip_name.split(', ')
    counts = collections.defaultdict(int)
    for count_text in count_texts:
        parts = count_text.split(' x ')
        num = int(parts[0])
        species = parts[1]
        counts[species] += num
    return(counts)


def score_clade_for_species(species, clade_species_counts, all_species_counts):
    species_count_in_clade = clade_species_counts[species]
    species_count_total = all_species_counts[species]
    genomes_in_clade = sum(clade_species_counts.values())

    fraction_of_species_in_clade = species_count_in_clade / species_count_total
    fraction_of_clade_that_is_species = species_count_in_clade / genomes_in_clade

    return fraction_of_species_in_clade * fraction_of_clade_that_is_species


def load_cluster_accessions():
    cluster_accessions = {}
    with open('cluster_accessions', 'rt') as accessions_file:
        for line in accessions_file:
            parts = line.split('\t')
            cluster_name = parts[0]
            accessions = [x[:-7] for x in parts[1].split(',')]
            cluster_accessions[cluster_name] = accessions
    return cluster_accessions


if __name__ == '__main__':
    main()
