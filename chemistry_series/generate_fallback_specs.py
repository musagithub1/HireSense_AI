from __future__ import annotations
import json
import re
from pathlib import Path

ROOT = Path(__file__).parent
items = json.loads((ROOT / 'curriculum.json').read_text())

MODULE_ARCS = {
    '01_chemistry_foundations': ('observe the substance', 'separate what changes from what stays conserved', 'connect particles to what we can see', 'use the model to explain an everyday example'),
    '02_measurement_and_math': ('name the quantity and unit', 'show how the measurement is made', 'track uncertainty through the calculation', 'check whether the answer is reasonable'),
    '03_atomic_theory': ('identify the atomic parts', 'show how the evidence supports the model', 'track particles or charge', 'use the model to interpret an element or ion'),
    '04_quantum_and_electronic_structure': ('place the electron in an allowed state', 'show energy changing in discrete steps', 'connect the state to a spectrum or property', 'use the pattern to predict another atom'),
    '05_periodicity': ('locate the element on the table', 'show nuclear charge and shielding', 'move across or down to reveal the trend', 'use the trend to compare elements'),
    '06_chemical_bonding': ('place the atoms near each other', 'show electrons redistributing', 'connect the bond to energy or properties', 'use the model to predict behavior'),
    '07_shape_polarity_and_forces': ('draw the particles or molecules', 'show the geometry or attraction', 'connect structure to a bulk property', 'use the pattern to compare substances'),
    '08_formulas_and_nomenclature': ('decompose the name or formula', 'match symbols to charges or groups', 'rebuild the complete chemical identity', 'use the decoding rule on a new example'),
    '09_stoichiometry_and_reactions': ('count the reacting particles', 'balance the chemical change', 'follow the limiting amount through the reaction', 'convert the particle story into a useful quantity'),
    '10_solutions': ('separate solute and solvent particles', 'show mixing or hydration', 'connect particle count to concentration or a property', 'use the model to predict dilution or solubility'),
    '11_gases': ('place gas particles in a container', 'change one macroscopic variable', 'show collisions causing the response', 'use the gas law to predict the next state'),
    '12_liquids_and_solids': ('arrange particles in the phase', 'change motion or attraction', 'show a phase transition or lattice property', 'use the particle picture to explain a material behavior'),
    '13_thermochemistry': ('define the system and surroundings', 'track energy entering or leaving', 'connect heat to particles or bonds', 'use the sign and scale to predict the process'),
    '14_thermodynamics': ('show the initial and final arrangements', 'count accessible microstates or energy pathways', 'combine enthalpy and entropy into free energy', 'use the sign to predict spontaneity'),
    '15_kinetics': ('place reactant particles on a reaction path', 'show collisions crossing an energy barrier', 'change temperature, concentration, or catalyst', 'use the rate pattern to compare outcomes'),
    '16_equilibrium': ('start with reactants and products', 'show forward and reverse motion', 'disturb one condition and follow the response', 'use the equilibrium expression to predict direction'),
    '17_acids_and_bases': ('show proton or electron-pair transfer', 'identify conjugate partners', 'connect the transfer to pH or equilibrium', 'use the relationship to predict a buffer or titration'),
    '18_solubility_and_complexation': ('place ions in solution and solid', 'show competing equilibria', 'highlight precipitation or complex formation', 'use the balance to predict selectivity'),
    '19_redox_and_electrochemistry': ('separate oxidation from reduction', 'route electrons through the cell', 'connect electron flow to potential or work', 'use the direction to predict a device or reaction'),
    '20_inorganic_chemistry': ('locate the element or complex', 'show the relevant orbitals or ligands', 'connect structure to color, reactivity, or function', 'use the periodic pattern to compare compounds'),
    '21_organic_foundations': ('draw the carbon framework', 'show electrons, shape, or stereochemistry', 'connect structure to reactivity or properties', 'use the representation to distinguish molecules'),
    '22_organic_reactions_and_mechanisms': ('place the reactant and reactive site', 'move electrons through the mechanism', 'show the intermediate or product forming', 'use the mechanism to predict selectivity'),
    '23_analytical_and_instrumental': ('start with an unknown sample', 'pass it through a measurement or separation', 'turn signal into chemical information', 'use calibration and uncertainty to report a result'),
    '24_biochemistry': ('show the biomolecule or cellular compartment', 'connect shape to interaction or energy transfer', 'follow the chemical transformation', 'use the mechanism to explain a biological outcome'),
    '25_materials_environment_nuclear_lab': ('define the material, environment, or nuclear system', 'show the particles, bonds, or energy flow', 'connect microscopic change to a real-world effect', 'use the chemistry to choose a safer or more useful outcome'),
}

IDIOMS = ['particles', 'molecular model', 'relationship network', 'stacking', 'distribution']

def cap(text: str) -> str:
    text = re.sub(r'\s+', ' ', text).strip()
    return text[:78]

out=[]
for item in items:
    a = MODULE_ARCS[item['module']]
    title = item['title']
    hook = f"How does {title.lower()} work?"
    claim = f"{title} becomes clear when we connect particles, structure, and change."
    beats = [
        {'caption': cap(f"Start with the idea: {title}."), 'visual_action': a[0], 'idiom': IDIOMS[0]},
        {'caption': cap("The key is how chemical parts relate."), 'visual_action': a[1], 'idiom': IDIOMS[1]},
        {'caption': cap("That relationship creates what we observe."), 'visual_action': a[2], 'idiom': IDIOMS[2]},
        {'caption': cap(f"Use the pattern to predict a new case."), 'visual_action': a[3], 'idiom': IDIOMS[3]},
    ]
    out.append({
        'number': item['number'], 'title': title, 'hook': hook,
        'teaching_claim': claim,
        'misconception': f"The name alone is not the explanation: the particle-level cause matters.",
        'takeaway': f"Understand {title.lower()} by linking structure to observable behavior.",
        'beats': beats,
        'closing': f"{title} is the link between chemical structure and what happens next."
    })
(ROOT/'episode_specs.json').write_text(json.dumps(out, indent=2, ensure_ascii=False)+'\n')
print(f'wrote {len(out)} fallback episode specs')
