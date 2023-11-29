"""
A pydantic schema for input options in pyscal-rdf

Interpreted from schema.yml
"""
from typing_extensions import Annotated
from typing import Any, Callable, List, ClassVar, Optional, Union, Literal
from pydantic import BaseModel, Field, ValidationError, model_validator, conlist, PrivateAttr
from pydantic.functional_validators import AfterValidator, BeforeValidator
from annotated_types import Len

import yaml
import numpy as np
import copy

def to_list(v: Any) -> List[Any]:
    return np.atleast_1d(v)


class CalculatedProperty(BaseModel, title='calculated property'):
    uri: str = Field('http://purls.helmholtz-metadaten.de/cmso/CalculatedProperty', frozen=True)
    label: Annotated[str, Field(default=None, uri='http://www.w3.org/2000/01/rdf-schema#label')]
    value: Annotated[Union[int, float], Field(default=None, uri='http://purls.helmholtz-metadaten.de/cmso/hasValue')]
    unit: Annotated[str, Field(default=None, uri='http://purls.helmholtz-metadaten.de/cmso/hasUnit')]

class SimulationCell(BaseModel, title='Simulation cell'):
    volume: Annotated[float, Field(default=0, ge=0, uri='http://purls.helmholtz-metadaten.de/cmso/hasVolume')]
    number_of_atoms: Annotated[int, Field(default=0, ge=0, uri='http://purls.helmholtz-metadaten.de/cmso/hasNumberOfAtoms')]
    length: Annotated[conlist(float, min_length=3, max_length=3), Field(default=[0,0,0], uri='http://purls.helmholtz-metadaten.de/cmso/SimulationCellLength')]
    vector: Annotated[conlist(conlist(float, min_length=3, max_length=3), 
        min_length=3, max_length=3), Field(default=None, uri='http://purls.helmholtz-metadaten.de/cmso/SimulationCellVector')]
    angle: Annotated[conlist(float, min_length=3, max_length=3), Field(default=[0,0,0], uri='http://purls.helmholtz-metadaten.de/cmso/SimulationCellAngle')]
    vacancy_concentration: Annotated[float, Field(default=0, ge=0, uri='http://purls.helmholtz-metadaten.de/podo/hasVacancyConcentration')]
    number_of_vacancies: Annotated[int, Field(default=0, ge=0, uri='http://purls.helmholtz-metadaten.de/podo/hasNumberOfVacancies')]

class UnitCell(BaseModel, title='Unit cell'):
    uri: str = Field('http://purls.helmholtz-metadaten.de/cmso/UnitCell', frozen=True)
    bravais_lattice: Annotated[str, Field(default=None, required=False)]
    lattice_parameter: Annotated[Union[float, conlist(float, min_length=3, max_length=3)],
        Field(default=0, required=False, uri='http://purls.helmholtz-metadaten.de/cmso/LatticeParameter')]
    angle: Annotated[conlist(float, min_length=3, max_length=3), Field(default=[90.0, 90.0, 90.0],
        required=False, uri='http://purls.helmholtz-metadaten.de/cmso/LatticeAngle')]

class CrystalStructure(BaseModel, title='Crystal structure'):
    uri: str = Field('http://purls.helmholtz-metadaten.de/cmso/CrystalStructure', frozen=True)
    altname: Annotated[str, Field(default=None, required=False, uri='http://purls.helmholtz-metadaten.de/cmso/hasAltName')]
    spacegroup_symbol: Annotated[str, Field(default=None, required=False, uri='http://purls.helmholtz-metadaten.de/cmso/hasSpaceGroupSymbol')]
    spacegroup_number: Annotated[int, Field(default=None, required=False, uri='http://purls.helmholtz-metadaten.de/cmso/hasSpaceGroupNumber')]
    unit_cell: Optional[UnitCell] = UnitCell()

class GrainBoundary(BaseModel, title='Grain boundary'):
    uri: str = Field('http://purls.helmholtz-metadaten.de/pldo/GrainBoundary', frozen=True)
    grain_boundary_type: Annotated[str, Field(default=None, required=False)]
    sigma: Annotated[int, Field(default=0, required=False, uri='http://purls.helmholtz-metadaten.de/pldo/hasSigmaValue')]
    plane: Annotated[conlist(float, min_length=3, max_length=3), Field(default=0, required=False, uri='http://purls.helmholtz-metadaten.de/pldo/hasGBplane')]
    rotation_axis: Annotated[conlist(float, min_length=3, max_length=3), Field(default=0, required=False, uri='http://purls.helmholtz-metadaten.de/pldo/hasRotationAxis')]
    misorientation_angle: Annotated[float, Field(default=0, required=False, uri='http://purls.helmholtz-metadaten.de/pldo/hasMisorientationAngle')]

class Defect(BaseModel, title='General defect class'):
    uri: str = Field('http://purls.helmholtz-metadaten.de/cmso/hasDefect', frozen=True)
    grain_boundary: Optional[GrainBoundary] = GrainBoundary()

class Material(BaseModel, title='Material'):
    uri: str = Field('http://purls.helmholtz-metadaten.de/cmso/Material', frozen=True)
    element_ratio: Annotated[dict, Field(default={}, 
        uri='http://purls.helmholtz-metadaten.de/cmso/hasElementRatio')]
    crystal_structure: Optional[CrystalStructure] = CrystalStructure()
    defect: Optional[Defect] = Defect()

class Sample(BaseModel, title='Sample'):
    uri: str = Field('http://purls.helmholtz-metadaten.de/cmso/AtomicScaleSample', frozen=True)
    material: Optional[Material] = Material()
    simulation_cell: Optional[SimulationCell] = SimulationCell()
    calculated_property: Optional[CalculatedProperty] = CalculatedProperty()
    #pass




