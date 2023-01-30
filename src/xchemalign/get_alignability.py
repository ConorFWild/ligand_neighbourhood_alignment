import gemmi
import numpy as np
from loguru import logger

from xchemalign.data import (
    LigandNeighbourhood,
    LigandNeighbourhoods,
    SystemData,
    Transform,
    Transforms,
)
from xchemalign.matching import match_atom


def match_cas(
    ligand_1_neighbourhood: LigandNeighbourhood,
    ligand_2_neighbourhood: LigandNeighbourhood,
    min_alignable_atoms: int = 5,
    max_alignable_rmsd: float = 2.0,
):

    alignable_cas = []
    for (
        ligand_1_atom_id,
        ligand_1_atom,
    ) in zip(ligand_1_neighbourhood.atom_ids, ligand_1_neighbourhood.atoms):
        for (ligand_2_atom_id, ligand_2_atom,) in zip(
            ligand_2_neighbourhood.atom_ids, ligand_2_neighbourhood.atoms
        ):
            if ligand_1_atom_id.atom == "CA":
                if match_atom(ligand_1_atom, ligand_2_atom, ignore_chain=True):
                    alignable_cas.append(
                        (
                            gemmi.Position(
                                ligand_1_atom.x,
                                ligand_1_atom.y,
                                ligand_1_atom.z,
                            ),
                            gemmi.Position(
                                ligand_2_atom.x,
                                ligand_2_atom.y,
                                ligand_2_atom.z,
                            ),
                        )
                    )

    if len(alignable_cas) > min_alignable_atoms:
        sup = gemmi.superpose_positions(
            [alignable_ca[0] for alignable_ca in alignable_cas],
            [alignable_ca[1] for alignable_ca in alignable_cas],
        )

        rmsd = sup.rmsd
        if rmsd < max_alignable_rmsd:
            return True, Transform(
                vec=sup.transform.vec.tolist(), mat=sup.transform.mat.tolist()
            )
        else:
            return False, None
    else:
        return False, None


def get_alignability(
    ligand_neighbourhoods: LigandNeighbourhoods,
    system_data: SystemData,
):

    # Get structures
    structures = {}
    for dataset in system_data.datasets:
        structure: gemmi.Structure = gemmi.read_structure(dataset.pdb)
        structures[dataset.dtag] = structure

    # Get connectivity matrix
    connectivity = []
    transform_ids = []
    transforms = []
    for (ligand_1_id, ligand_1_neighbourhood) in zip(
        ligand_neighbourhoods.ligand_ids,
        ligand_neighbourhoods.ligand_neighbourhoods,
    ):
        connectivities = []
        for (ligand_2_id, ligand_2_neighbourhood,) in zip(
            ligand_neighbourhoods.ligand_ids,
            ligand_neighbourhoods.ligand_neighbourhoods,
        ):
            # See if atoms match - transform is frame 2 to frame 1
            ca_match, transform = match_cas(
                ligand_1_neighbourhood, ligand_2_neighbourhood
            )

            if ca_match:
                connectivities.append(1)
                transform_ids.append((ligand_1_id, ligand_2_id))
                transforms.append(transform)
            else:
                connectivities.append(0)

        connectivity.append(connectivities)

    logger.debug(connectivity)

    return np.array(connectivity), Transforms(
        ligand_ids=transform_ids, transforms=transforms
    )
