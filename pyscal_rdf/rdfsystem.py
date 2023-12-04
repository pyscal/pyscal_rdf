import numpy as np
from functools import partial, update_wrapper

import pyscal3.core as pc
from pyscal3.atoms import AttrSetter
import pyscal_rdf.properties as prp

from rdflib import Graph, Literal, Namespace, XSD, RDF, RDFS, BNode, URIRef, FOAF, SKOS, DCTERMS

CMSO = Namespace("https://purls.helmholtz-metadaten.de/cmso/")
PLDO = Namespace("https://purls.helmholtz-metadaten.de/pldo/")
PODO = Namespace("https://purls.helmholtz-metadaten.de/podo/")

class System(pc.System):
    def __init__(self, filename = None, 
            format = "lammps-dump", 
            compressed = False, 
            customkeys = None,
            source=None):
        super().__init__(filename = filename, 
            format = format, 
            compressed = compressed, 
            customkeys = customkeys)
        #this is the sample which will be stored
        self.sample = None
        #the graph object should also be attached
        #for post-processing of structures
        self.graph = None
        self._atom_ids = None
        if source is not None:
            self.__dict__.update(source.__dict__)

        #assign attributes
        self.schema = AttrSetter()
        mapdict = {
        "material": {
            "element_ratio": partial(prp.get_chemical_composition, self),
            "crystal_structure": {
                "name": partial(prp.get_crystal_structure_name, self),
                "spacegroup_symbol": partial(prp.get_spacegroup_symbol, self),
                "spacegroup_number": partial(prp.get_spacegroup_number, self),
                "unit_cell": {
                    "bravais_lattice": partial(prp.get_bravais_lattice, self),
                    "lattice_parameter": partial(prp.get_lattice_parameter, self),
                    "angle": partial(prp.get_lattice_angle, self),
                    },            
                },        
            },
        "simulation_cell": {
            "volume": partial(prp.get_cell_volume, self),
            "number_of_atoms": partial(prp.get_number_of_atoms, self),
            "length": partial(prp.get_simulation_cell_length, self),
            "vector": partial(prp.get_simulation_cell_vector, self),
            "angle": partial(prp.get_simulation_cell_angle, self),
            },
        "atom_attribute": {
            "position": partial(prp.get_position, self),
            "species": partial(prp.get_species, self),
            },
        }

        self.schema._add_attribute(mapdict)


    def __delitem__(self, val):
        if isinstance(val, int):
            val = [val]
        #now the graph has to be updated accordingly
        if self.graph is not None:
            #first annotate graph
            c = (len(val)/self.natoms)
            self.graph.add_vacancy(c, number=len(val))
            #now we need to re-add atoms, so at to remove
            #deleted ones from the vacancy
            atoms = [self._atom_ids[v] for v in val] 
            #this is the list of atoms in this sample
            for atom in atoms:
                #identify the position
                position = list([s[2] for s in self.graph.graph.triples((atom, CMSO.hasPositionVector, None))])[0]
                self.graph.graph.remove((position, None, None))
                #identify element
                element = list([s[2] for s in self.graph.graph.triples((atom, CMSO.hasElement, None))])[0]
                self.graph.graph.remove((element, None, None))
                #now remove the atom from the list completely
                self.graph.graph.remove((atom, None, None))
                self.graph.graph.remove((None, None, atom))
            #now fully remove atoms
            for atom in atoms:
                self._atom_ids.remove(atom)
            #now fix the number of atoms
            self.graph.graph.remove((self.sample, CMSO.hasNumberOfAtoms, None))
            self.graph.graph.add((self.sample, CMSO.hasNumberOfAtoms, Literal(self.natoms-len(val), datatype=XSD.integer)))
            #revamp composition
            #for that first get element
            material = list([s[2] for s in self.graph.graph.triples((self.sample, CMSO.hasMaterial, None))])[0]
            #remove existing chem composution
            self.graph.graph.remove((material, CMSO.hasElementRatio, None))
            #now recalculate and add it again
            chem_comp_element = list(self.composition.keys())
            chem_comp_ratio = [val for key, val in self.composition.items()]
            chem_comp = ["=".join([str(x), str(y)]) for x,y in zip(chem_comp_element, chem_comp_ratio)]
            for x in range(len(chem_comp)):
                self.graph.graph.add((material, CMSO.hasElementRatio, Literal(chem_comp[x], datatype=XSD.string)))
        self.delete(indices=list(val))