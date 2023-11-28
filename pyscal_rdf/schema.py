"""
A pydantic schema for input options in pyscal-rdf

Interpreted from schema.yml
"""
from typing_extensions import Annotated
from typing import Any, Callable, List, ClassVar, Optional, Union
from pydantic import BaseModel, Field, ValidationError, model_validator, conlist, PrivateAttr
from pydantic.functional_validators import AfterValidator, BeforeValidator
from annotated_types import Len

import yaml
import numpy as np
import copy

def to_list(v: Any) -> List[Any]:
    return np.atleast_1d(v)


class CalculatedProperty(BaseModel, title='calculated property'):
	label: Annotated[str, Field(default=None)]
	value: Annotated[Union[int, float], Field(default=None)]
	unit: Annotated[str, Field(default=None)]

class SimulationCell(BaseModel, title='Simulation cell'):
	volume: Annotated[float, Field(default=0, ge=0)]
	number_of_atoms: Annotated[int, Field(default=0, ge=0)]
	length: Annotated[conlist(float, min_length=3, max_length=3), Field(default=0, ge=0)]
	vector: Annotated[conlist(conlist(float, min_length=3, max_length=3), 
		min_length=3, max_length=3), Field(default=0)]
	angle: Annotated[conlist(float, min_length=3, max_length=3), Field(default=0, ge=0)]
	vacancy_concentration: Annotated[float, Field(default=0, ge=0)]
	number_of_vacancies: Annotated[int, Field(default=0, ge=0)]

class UnitCell(BaseModel, title='Unit cell'):
	bravais_lattice: Annotated[str, Field(default=None, required=False)]
	lattice_parameter: Annotated[Union[float, conlist(float, min_length=3, max_length=3)],
		Field(default=0), required=False]
	angle: Annotated[conlist(float, min_length=3, max_length=3), Field(default=[90.0, 90.0, 90.0],
		required=False)]

class CrystalStructure(BaseModel, title='Crystal structure'):
	altname: Annotated[str, Field(default=None, required=False)]
	spacegroup_symbol: Annotated[str, Field(default=None, required=False)]
	spacegroup_number: Annotated[int, Field(default=None, required=False)]
	unit_cell: Optional[UnitCell] = UnitCell()

class GrainBoundary(BaseModel, title='Grain boundary'):
	grain_boundary_type: Annotated[str, Field(default=None, required=False)]
	sigma: Annotated[int, Field(default=0, required=False)]
	plane: Annotated[conlist(float, min_length=3, max_length=3), Field(default=0, required=False)]
	rotation_axis: Annotated[conlist(float, min_length=3, max_length=3), Field(default=0, required=False)]
	misorientation_angle: Annotated[float, Field(default=0, required=False)]

class Defect(BaseModel, title='General defect class'):
	grain_boundary: Optional[GrainBoundary] = GrainBoundary()

class Material(BaseModel, title='Material'):
	element_ratio: Annotated[dict]
	crystal_structure: Optional[CrystalStructure] = CrystalStructure()
	defect: Optional[Defect] = Defect()
	
class Sample(BaseModel, title='Sample'):
	material: Optional[Material] = Material()
	simulation_cell: Optional[SimulationCell] = SimulationCell()
	calculated_property[CalculatedProperty] = CalculatedProperty()





