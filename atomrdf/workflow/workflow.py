"""
Workflows aspects for non-automated annotation of structures.

This consists of a workflow class which implements the necessary methods to serialise triples as needed.
Custom workflow solutions can be implemented. An example available here is pyiron.
The custom workflow env should implement the following functions:

_check_if_job_is_valid
_add_structure
_identify_method
extract_calculated_properties
inform_graph

See atomrdf.workflow.pyiron for more details
"""

from rdflib import Literal, Namespace, XSD, RDF, RDFS, BNode, URIRef

import warnings
import numpy as np
import os
import copy
import ast
import uuid

from atomrdf.structure import System

#Move imports to another file
from atomrdf.namespace import PROV, CMSO, PODO, ASMO

#custom imports as needed
import atomrdf.workflow.pyiron as pi


class Workflow:
    def __init__(self, kg, 
        environment='pyiron'):
        """
        Initialize the workflow environment

        Parameters
        ----------
        kg: pyscal-rdf KnowledgeGraph
        environment: string
            the workflow environment. This is used to import the necessary functions.

        """
        self.kg = kg
        if environment == 'pyiron':
            self.wenv = pi
        else:
            raise ValueError('unknown workflow environment')

    def _prepare_job(self, workflow_object):

        self.wenv._check_if_job_is_valid(workflow_object)
        parent_structure, parent_sample, structure, sample = self.wenv._add_structures(workflow_object)
        method_dict = self.wenv._identify_method(workflow_object)

        if (structure is None) and (sample is None):
            raise ValueError('Either structure or sample should be specified')

        if sample is None:
            #its not added to graph yet
            structure.graph = self.kg
            structure.to_graph()
            sample = structure.sample
        
        if parent_sample is None:
            #its not added to graph yet
            if parent_structure is not None:
                parent_structure.graph = self.kg
                parent_structure.to_graph()
                parent_sample = parent_structure.sample

        self.structure = structure
        self.sample = sample
        self.mdict = method_dict
        self.main_id = method_dict['id']
        self.parent_sample = parent_sample

    def _get_lattice_properties(self, ):
        if self.parent_sample is None:
            return
        
        material = list([k[2] for k in self.kg.triples((self.parent_sample, CMSO.hasMaterial, None))])[0]
        crystal_structure = self.kg.value(material, CMSO.hasStructure)
        
        altname = self.kg.value(crystal_structure, CMSO.hasAltName)
        
        space_group = self.kg.value(crystal_structure, CMSO.hasSpaceGroup)
        space_group_symbol = self.kg.value(space_group, CMSO.hasSpaceGroupSymbol)
        space_group_number = self.kg.value(space_group, CMSO.hasSpaceGroupNumber)

        unit_cell = self.kg.value(crystal_structure, CMSO.hasUnitCell)
        blattice = self.kg.value(unit_cell, Namespace("http://purls.helmholtz-metadaten.de/cmso/").hasBravaisLattice)

        lattice_parameter = self.kg.value(unit_cell, CMSO.hasLatticeParameter)
        lattice_parameter_x = self.kg.value(lattice_parameter, CMSO.hasLength_x)
        lattice_parameter_y = self.kg.value(lattice_parameter, CMSO.hasLength_y)
        lattice_parameter_z = self.kg.value(lattice_parameter, CMSO.hasLength_z)

        lattice_angle = self.kg.value(unit_cell, CMSO.hasAngle)
        lattice_angle_x = self.kg.value(lattice_angle, CMSO.hasAngle_alpha)
        lattice_angle_y = self.kg.value(lattice_angle, CMSO.hasAngle_beta)
        lattice_angle_z = self.kg.value(lattice_angle, CMSO.hasAngle_gamma)

        targets = [altname, space_group_symbol, space_group_number, blattice,
        [lattice_parameter_x, lattice_parameter_y, lattice_parameter_z],
        [lattice_angle_x, lattice_angle_y, lattice_angle_z]]

        self.structure._add_crystal_structure(targets=targets)


    def _add_inherited_properties(self, ):
        #Here we need to add inherited info: CalculatedProperties will be lost
        #Defects will be inherited
        if self.parent_sample is None:
            return

        parent_material = list([k[2] for k in self.kg.triples((self.parent_sample, CMSO.hasMaterial, None))])[0]
        parent_defects = list([x[2] for x in self.kg.triples((parent_material, CMSO.hasDefect, None))])
        #now for each defect we copy add this to the final sample
        material = list([k[2] for k in self.kg.triples((self.sample, CMSO.hasMaterial, None))])[0]

        for defect in parent_defects:
            new_defect = URIRef(defect.toPython())
            self.kg.graph.add((material, CMSO.hasDefect, new_defect))
            #now fetch all defect based info
            for triple in self.kg.triples((defect, None, None)):
                self.kg.graph.add((new_defect, triple[1], triple[2]))

        #now add the special props for vacancy
        parent_simcell = self.kg.value(self.sample, CMSO.hasSimulationCell)
        simcell = self.kg.value(self.parent_sample, CMSO.hasSimulationCell) 
        
        for triple in self.kg.triples((parent_simcell, PODO.hasVacancyConcentration, None)):
            self.kg.graph.add((simcell, triple[1], triple[2]))
        for triple in self.kg.triples((parent_simcell, PODO.hasNumberOfVacancies, None)):
            self.kg.graph.add((simcell, triple[1], triple[2]))



    def add_structural_relation(self, ):
        self.kg.add((self.sample, RDF.type, PROV.Entity))
        if self.parent_sample is not None:
            self.kg.add((self.parent_sample, RDF.type, PROV.Entity))
            self.kg.add((self.sample, PROV.wasDerivedFrom, self.parent_sample))
            self._get_lattice_properties()
            self._add_inherited_properties()


    def add_method(self, ):
        """
        mdict
        -----
        md:

        """
        if self.mdict is None:
            return
        
        #add activity
        #----------------------------------------------------------
        activity = URIRef(f'activity_{main_id}')
        self.kg.add((activity, RDF.type, PROV.Activity))

        #add method
        #----------------------------------------------------------
        method = URIRef(f'method_{self.main_id}')
        if self.mdict['method'] == 'MolecularStatics':
            self.kg.add((method, RDF.type, ASMO.MolecularStatics))
        elif self.mdict['method'] == 'MolecularDynamics':
            self.kg.add((method, RDF.type, ASMO.MolecularDynamics))
        elif self.mdict['method'] == 'DensityFunctionalTheory':
            self.kg.add((method, RDF.type, ASMO.DensityFunctionalTheory))
        self.kg.add((activity, ASMO.hasComputationalMethod, method))

        #choose if its rigid energy or structure optimisation
        #----------------------------------------------------------        
        if len(self.mdict['dof']) == 0:
            self.kg.add((activity, RDF.type, Namespace("http://purls.helmholtz-metadaten.de/asmo/").RigidEnergyCalculation))
        else:
            self.kg.add((activity, RDF.type, ASMO.StructureOptimization))
        #add DOFs
        for dof in self.mdict['dof']:
            self.kg.add((activity, ASMO.hasRelaxationDOF, getattr(ASMO, dof)))

        #add method specific items
        if self.mdict['method'] in ['MolecularStatics', 'MolecularDynamics']:
            self._add_md()
        elif self.mdict['method'] in ['DensityFunctionalTheory']:
            self._add_dft()

        #add that structure was generated
        self.kg.add((self.sample, PROV.wasGeneratedBy, activity))
        self._add_inputs(activity)
        self._add_outputs(activity)
        self._add_software(method, activity)     


    def to_graph(self, workflow_object):
        self._prepare_job(workflow_object)
        self.add_structural_relation()
        self.add_method()

    
    def _add_outputs(self, activity):
        for key, val in self.mdict['outputs'].items():
            prop = URIRef(f'{self.main_id}_{key}')
            self.kg.add((prop, RDF.type, CMSO.CalculatedProperty))
            self.kg.add((prop, RDFS.label, Literal(key)))
            self.kg.add((prop, ASMO.hasValue, Literal(val["value"])))
            if "unit" in val.keys():
                unit = val['unit']
                self.kg.add((prop, ASMO.hasUnit, URIRef(f'http://qudt.org/vocab/unit/{unit}')))
            self.kg.add((prop, ASMO.wasCalculatedBy, activity))
            if val['associate_to_sample']:
                self.kg.add((self.sample, CMSO.hasCalculatedProperty, prop))

    def _add_inputs(self, activity):
        for key, val in self.mdict['inputs'].items():
            prop = URIRef(f'{self.main_id}_{key}')
            self.kg.add((prop, RDF.type, CMSO.InputParameter))
            self.kg.add((prop, RDFS.label, Literal(key)))
            self.kg.add((prop, ASMO.hasValue, Literal(val["value"])))
            if "unit" in val.keys():
                unit = val['unit']
                self.kg.add((prop, ASMO.hasUnit, URIRef(f'http://qudt.org/vocab/unit/{unit}')))
            self.kg.add((activity, ASMO.hasInputParameter, prop))

    def _add_software(self, method):
        #finally add software
        wfagent = None
        if 'workflow_manager' in self.mdict.keys():
            wfagent = URIRef(self.mdict["workflow_manager"]['uri'])
            self.kg.add((wfagent, RDF.type, PROV.SoftwareAgent))
            self.kg.add((wfagent, RDFS.label, Literal(self.mdict["workflow_manager"]['label'])))
            self.kg.add((method, PROV.wasAssociatedWith, wfagent))

        for software in self.mdict['software']:
            agent = URIRef(software['uri'])
            self.kg.add((agent, RDF.type, PROV.SoftwareAgent))
            self.kg.add((agent, RDFS.label, Literal(software['label'])))
            if wfagent is not None:
                self.kg.add((wfagent, PROV.actedOnBehalfOf, agent))
            else:
                self.kg.add((method, PROV.wasAssociatedWith, agent))


    def _add_md(self, method, activity):
        self.kg.add((method, ASMO.hasStatisticalEnsemble, getattr(ASMO, self.mdict['ensemble'])))

        #add temperature if needed
        if self.mdict['temperature'] is not None:
            temperature = URIRef(f'temperature:{self.main_id}')
            self.kg.add((temperature, RDF.type, ASMO.InputParameter))
            self.kg.add((temperature, RDFS.label, Literal('temperature', datatype=XSD.string)))
            self.kg.add((activity, ASMO.hasInputParameter, temperature))
            self.kg.add((temperature, ASMO.hasValue, Literal(self.mdict['temperature'], datatype=XSD.float)))
            self.kg.add((temperature, ASMO.hasUnit, URIRef('http://qudt.org/vocab/unit/K')))

        if mdict['pressure'] is not None:
            pressure = URIRef(f'pressure:{self.main_id}')
            self.kg.add((pressure, RDF.type, ASMO.InputParameter))
            self.kg.add((pressure, RDFS.label, Literal('pressure', datatype=XSD.string)))
            self.kg.add((activity, ASMO.hasInputParameter, pressure))
            self.kg.add((pressure, ASMO.hasValue, Literal(self.mdict['pressure'], datatype=XSD.float)))
            self.kg.add((pressure, ASMO.hasUnit, URIRef('http://qudt.org/vocab/unit/GigaPA')))

        #potentials need to be mapped
        potential = URIRef(f'potential:{self.main_id}')
        if 'meam' in self.mdict['potential']['type']:
            self.kg.add((potential, RDF.type, ASMO.ModifiedEmbeddedAtomModel))
        elif 'eam' in self.mdict['potential']['type']:
            self.kg.add((potential, RDF.type, ASMO.EmbeddedAtomModel))
        elif 'lj' in self.mdict['potential']['type']:
            self.kg.add((potential, RDF.type, ASMO.LennardJonesPotential))
        elif 'ace' in self.mdict['potential']['type']:
            self.kg.add((potential, RDF.type, ASMO.MachineLearningPotential))
        else:
            self.kg.add((potential, RDF.type, ASMO.InteratomicPotential))

        if 'uri' in self.mdict['potential'].keys():
            self.kg.add((potential, CMSO.hasReference, Literal(mdict['potential']['uri'], datatype=XSD.string)))
        if 'label' in self.mdict['potential'].keys():
            self.kg.add((potential, RDFS.label, Literal(mdict['potential']['label'])))

        self.kg.add((method, ASMO.hasInteratomicPotential, potential))
