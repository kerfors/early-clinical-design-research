"""Build cpmp-soa-join/cpmp_soa_join.ipynb with the json module.

Run from the early-clinical-design-research folder:
    python3 scripts/build_cpmp_join_notebook.py
"""
import json
from pathlib import Path

OUT = Path('cpmp-soa-join/cpmp_soa_join.ipynb')


def lines(text):
    text = text.strip('\n') + '\n'
    parts = text.split('\n')[:-1]
    return [p + '\n' for p in parts[:-1]] + [parts[-1]]


def markdown_cell(text):
    return {'cell_type': 'markdown', 'metadata': {}, 'source': lines(text)}


def code_cell(text):
    return {'cell_type': 'code', 'execution_count': None, 'metadata': {},
            'outputs': [], 'source': lines(text)}


cells = []

cells.append(markdown_cell('''
# CPMP SoA join: master + ISA, allocation kind per activity × visit

Lilly Chronic Pain Master Protocol (CPMP): master SoA (NCT05986292) and 12 ISA SoAs, a 4 compound × 3 disease-state grid. The disease-state addenda (DSA) are not public, so the DSA SoA layer is missing.

**Question.** How does allocation between layers (delegation, restatement, addition, extension, override) show in the SoA, cell by cell, across the grid?

**Sources.** Consolidated outputs of the soa2usdm collection `cpmp` (`soa2usdm-collections/collections/cpmp`, commit `cf9541d`), and `studies_protocols.xlsx` there for layer, compound and disease state. Read only.

**Activity identity.** Layers name the same activity differently (AE / AEs / Adverse events). `activity_crosswalk.csv` maps printed names to an activity key. Non-identical entries are proposals for review (`status = proposed`); `use = no` keeps a name as its own key. No fuzzy matching.

**Rules.**
- Document content only. A cell kind is derived by rule from master and ISA marks; a cross-layer statement is document-stated text, its kind is rule-derived from a text pattern.
- Content common across ISAs of one disease state is "common across these ISAs", never DSA content.
- The DSA SoA is unknown: a master-only cell may be changed by a DSA, an ISA-only cell may restate a DSA. The kinds below say what master and ISA show, nothing more.
'''))

cells.append(markdown_cell('''
## Cell kinds (per ISA, activity key × visit)

| kind | master mark | ISA mark | activity in master SoA | visit in master SoA |
|---|---|---|---|---|
| `inherited` | X | – | yes | yes |
| `restated` | X | X | yes | yes |
| `added` | – | X | yes | yes |
| `extended` | – | X | yes | no |
| `isa_only` | – | X | no | yes |
| `isa_only_extended` | – | X | no | no |

Cross-layer statements (text patterns, applied to annotations bound to activities or to the visit row):

| statement kind | pattern | layer | effect on cells |
|---|---|---|---|
| `delegation_activity` | "included in each ISA" / "defined in each respective ISA" | master | activity flag: the master hands post-randomization marks to the ISA |
| `delegation_visits` | "Visits after V7 may be specified in the ISA" | master | visit flag: ISA visits after V7 |
| `override_ed` | "not needed for ED per the CPMP SoA" | ISA | the ED cell of the activity becomes `override_ed` |
| `addition_stated` | "in addition to schedule described in" | ISA | ISA marks of the activity carry the flag; the text names master only or master + DSA |
'''))

cells.append(code_cell('''
import json
import re
from pathlib import Path

import pandas as pd

COLLECTION = Path('../../GitHub/soa2usdm-collections/collections/cpmp')
CROSSWALK = Path('activity_crosswalk.csv')
OUT = Path('output')
MASTER = 'NCT05986292'

OUT.mkdir(exist_ok=True)
assert COLLECTION.is_dir(), f'collection not found: {COLLECTION.resolve()}'
pd.set_option('display.width', 200)
pd.set_option('display.max_columns', 30)
pd.set_option('display.max_colwidth', 80)
'''))

cells.append(markdown_cell('''
## 1. Studies: layer, compound, disease state
'''))

cells.append(code_cell('''
studies = pd.read_excel(COLLECTION / 'studies_protocols.xlsx', sheet_name='studies')
studies = studies[['nct_id', 'study_code', 'cpmp_layer', 'disease_state_addendum', 'compound']].copy()
studies['isa'] = studies['study_code'].str.replace('H0P-MC-', '', regex=False)
studies['disease'] = studies['disease_state_addendum'].str.split(' ').str[-1]
assert (studies['cpmp_layer'] == 'master').sum() == 1
assert studies.loc[studies['cpmp_layer'] == 'master', 'nct_id'].item() == MASTER
isas = studies[studies['cpmp_layer'] == 'ISA'].sort_values(['compound', 'disease']).reset_index(drop=True)
assert len(isas) == 12
isas
'''))

cells.append(markdown_cell('''
## 2. Marks from the consolidated outputs

One row per activity × visit with an X. Visits are identified by the visit-number value (V1 … V803, ED); the visit-name row (e.g. "Randomization to ISA") is not used for the join. Section-header activities are left out.
'''))

cells.append(code_cell('''
VISIT_NO = re.compile(r'^(V\\s?\\d+|ED)$')


def visit_number(col):
    values = [p['value'].strip() for p in col['property_values']
              if p['property_type'] == 'visit' and VISIT_NO.match(p['value'].strip())]
    assert len(values) == 1, f"no single visit number in {col['composite_label']}"
    return values[0].replace(' ', '')


def load(nct):
    path = COLLECTION / 'protocols' / nct / 'SoA2USDM' / 'consolidated' / f'{nct}_consolidated.json'
    d = json.load(open(path, encoding='utf-8'))
    assert list(d['timeline_segments']) == ['main'], f'{nct}: more than one timeline segment'
    cols = {c['xcol_id']: visit_number(c) for c in d['timeline_segments']['main']}
    acts = {a['xact_id']: a for a in d['unified_activities']}
    visits = list(cols.values())
    activities = [a['activity_name'] for a in d['unified_activities'] if not a['is_section_header']]
    marks = []
    for m in d['schedule_matrix']:
        if not str(m['consolidated_value']).strip():
            continue
        a = acts[m['xact_id']]
        assert not a['is_section_header'], f"{nct}: mark on section header {a['activity_name']}"
        marks.append({'nct_id': nct, 'activity_name': a['activity_name'], 'visit': cols[m['xcol_id']]})
    notes = []
    for n in d['unified_annotations']:
        notes.append({'nct_id': nct, 'text': n['annotation_text'],
                      'activities': [acts[x]['activity_name'] for x in n['referenced_xacts']],
                      'props': list(n['referenced_props'])})
    return visits, activities, pd.DataFrame(marks), notes


VISITS, ACTIVITIES, mark_frames, NOTES = {}, {}, [], []
for nct in [MASTER] + isas['nct_id'].tolist():
    v, a, m, n = load(nct)
    VISITS[nct], ACTIVITIES[nct] = v, a
    mark_frames.append(m)
    NOTES.extend(n)
marks = pd.concat(mark_frames, ignore_index=True)
marks.groupby('nct_id').size().rename('marks').to_frame().join(
    pd.Series({k: ', '.join(v) for k, v in VISITS.items()}, name='visits'))
'''))

cells.append(markdown_cell('''
## 3. Activity keys from the crosswalk

Every printed name must be in the crosswalk (fail fast otherwise). The table lists the non-identical entries in use, and how many marks depend on each.
'''))

cells.append(code_cell('''
xw = pd.read_csv(CROSSWALK, dtype=str).fillna('')
assert xw['name_as_printed'].is_unique
assert set(xw['use']) <= {'yes', 'no'}
all_names = {n for names in ACTIVITIES.values() for n in names}
missing = sorted(all_names - set(xw['name_as_printed']))
assert not missing, f'names not in crosswalk: {missing}'
xw['key'] = xw['activity_key'].where(xw['use'] == 'yes', xw['name_as_printed'])
KEY = dict(zip(xw['name_as_printed'], xw['key']))
marks['activity_key'] = marks['activity_name'].map(KEY)
ACT_KEYS = {nct: {KEY[n] for n in names} for nct, names in ACTIVITIES.items()}

used = xw[(xw['basis'] != 'identical') & (xw['use'] == 'yes')][['name_as_printed', 'activity_key', 'basis', 'status']]
used = used.merge(marks.groupby('activity_name').size().rename('marks'),
                  left_on='name_as_printed', right_index=True, how='left').fillna({'marks': 0}).astype({'marks': int})
used
'''))

cells.append(markdown_cell('''
## 4. Cross-layer statements

Annotations whose text matches one of the four patterns. The text is document-stated; the kind is rule-derived.
'''))

cells.append(code_cell('''
PATTERNS = [
    ('delegation_activity', re.compile(r'included in each ISA|defined in each respective ISA', re.I)),
    ('delegation_visits', re.compile(r'Visits after V7 may be specified in the ISA', re.I)),
    ('override_ed', re.compile(r'not needed for ED per the CPMP SoA', re.I)),
    ('addition_stated', re.compile(r'in addition to schedule described in', re.I)),
]

rows = []
for n in NOTES:
    for kind, pat in PATTERNS:
        if pat.search(n['text']):
            rows.append({'nct_id': n['nct_id'], 'statement_kind': kind,
                         'activities': [KEY[a] for a in n['activities']],
                         'names_dsa': bool(re.search(r'\\bDSA\\b', n['text'])),
                         'text': n['text']})
statements = pd.DataFrame(rows)
statements = statements.merge(studies[['nct_id', 'isa']], on='nct_id')
assert set(statements.loc[statements['statement_kind'].str.startswith('delegation'), 'nct_id']) == {MASTER}
assert set(statements.loc[~statements['statement_kind'].str.startswith('delegation'), 'nct_id']) <= set(isas['nct_id'])
statements[['isa', 'statement_kind', 'names_dsa', 'activities', 'text']]
'''))

cells.append(code_cell('''
DELEGATED_ACTS = {a for acts in statements.loc[statements['statement_kind'] == 'delegation_activity', 'activities'] for a in acts}
visit_rows = statements[statements['statement_kind'] == 'delegation_visits']
assert len(visit_rows) == 1
OVERRIDE = {(r.nct_id, a) for r in statements[statements['statement_kind'] == 'override_ed'].itertuples() for a in r.activities}
ADDITION = {(r.nct_id, a): ('master + DSA' if r.names_dsa else 'master only')
            for r in statements[statements['statement_kind'] == 'addition_stated'].itertuples() for a in r.activities}
print('activities delegated by the master:', sorted(DELEGATED_ACTS))
'''))

cells.append(markdown_cell('''
## 5. Layered grid: one row per ISA × activity key × visit

For each ISA: the union of master and ISA activity keys × the union of master and ISA visits, keeping only cells with a mark in either layer.

`visit_after_v7` flags ISA visits that the master's visit-row statement covers ("Visits after V7 may be specified in the ISA"); ED is not counted as after V7.
'''))

cells.append(code_cell('''
def visit_order(v):
    return (2, 0) if v == 'ED' else (1, int(v[1:])) if int(v[1:]) >= 100 else (0, int(v[1:]))


master_marks = set(zip(marks.loc[marks['nct_id'] == MASTER, 'activity_key'], marks.loc[marks['nct_id'] == MASTER, 'visit']))
master_visits = set(VISITS[MASTER])
master_keys = ACT_KEYS[MASTER]

grid_rows = []
for isa in isas.itertuples():
    isa_marks = set(zip(marks.loc[marks['nct_id'] == isa.nct_id, 'activity_key'], marks.loc[marks['nct_id'] == isa.nct_id, 'visit']))
    for key, visit in sorted(master_marks | isa_marks):
        in_m, in_i = (key, visit) in master_marks, (key, visit) in isa_marks
        if in_m and visit not in VISITS[isa.nct_id]:
            kind = 'inherited'
        elif in_m and in_i:
            kind = 'restated'
        elif in_m:
            kind = 'inherited'
        elif key in master_keys:
            kind = 'added' if visit in master_visits else 'extended'
        else:
            kind = 'isa_only' if visit in master_visits else 'isa_only_extended'
        if visit == 'ED' and (isa.nct_id, key) in OVERRIDE:
            kind = 'override_ed'
        grid_rows.append({
            'isa': isa.isa, 'nct_id': isa.nct_id, 'compound': isa.compound, 'disease': isa.disease,
            'activity_key': key, 'visit': visit, 'master_mark': in_m, 'isa_mark': in_i, 'kind': kind,
            'delegated_by_master': key in DELEGATED_ACTS,
            'visit_after_v7': visit != 'ED' and visit_order(visit) > visit_order('V7'),
            'addition_stated': ADDITION.get((isa.nct_id, key), '') if in_i else '',
        })
# ED cells with an override statement but no mark in either layer
for (nct, key) in sorted(OVERRIDE):
    row = isas[isas['nct_id'] == nct].iloc[0]
    if not any(r['nct_id'] == nct and r['activity_key'] == key and r['visit'] == 'ED' for r in grid_rows):
        grid_rows.append({
            'isa': row.isa, 'nct_id': nct, 'compound': row.compound, 'disease': row.disease,
            'activity_key': key, 'visit': 'ED', 'master_mark': False, 'isa_mark': False,
            'kind': 'override_ed', 'delegated_by_master': key in DELEGATED_ACTS,
            'visit_after_v7': False, 'addition_stated': '',
        })
grid = pd.DataFrame(grid_rows)
grid['in_master_soa'] = grid['activity_key'].isin(master_keys)
grid.to_csv(OUT / 'layered_grid.csv', index=False)
print(len(grid), 'cells')
grid.head()
'''))

cells.append(markdown_cell('''
### Check: every mark is accounted for

Each ISA mark appears once with `isa_mark = True`; each master mark appears once per ISA with `master_mark = True`.
'''))

cells.append(code_cell('''
for isa in isas.itertuples():
    g = grid[grid['nct_id'] == isa.nct_id]
    n_isa = int((marks['nct_id'] == isa.nct_id).sum())
    assert g['isa_mark'].sum() == n_isa, f'{isa.isa}: {g["isa_mark"].sum()} != {n_isa}'
    assert g['master_mark'].sum() == len(master_marks), f'{isa.isa}: master marks'
    assert not g.duplicated(['activity_key', 'visit']).any(), f'{isa.isa}: duplicate cells'
print('marks accounted for: master', len(master_marks), 'per ISA; ISA marks', int(grid['isa_mark'].sum()), 'in total')
'''))

cells.append(markdown_cell('''
## 6. Allocation kinds per ISA

Rows ordered by compound, then disease state. `inherited` counts master cells the ISA does not restate.
'''))

cells.append(code_cell('''
KINDS = ['inherited', 'restated', 'added', 'extended', 'isa_only', 'isa_only_extended', 'override_ed']
summary = grid.pivot_table(index=['compound', 'disease', 'isa'], columns='kind', values='visit',
                           aggfunc='count', fill_value=0).reindex(columns=KINDS, fill_value=0)
summary['isa_marks'] = grid[grid['isa_mark']].groupby(['compound', 'disease', 'isa']).size()
summary.to_csv(OUT / 'kinds_per_isa.csv')
summary
'''))

cells.append(markdown_cell('''
## 7. Compound column: is the ISA schedule the same across disease states?

For each compound, the ISA cells (activity key × visit with an ISA mark) of the three disease states. `in_all_3` = cells marked in all three ISAs of the compound.
'''))

cells.append(code_cell('''
isa_cells = grid[grid['isa_mark']][['compound', 'disease', 'isa', 'activity_key', 'visit']]
col_rows = []
for comp, g in isa_cells.groupby('compound'):
    sets = {d: set(zip(x['activity_key'], x['visit'])) for d, x in g.groupby('disease')}
    union = set.union(*sets.values())
    common = set.intersection(*sets.values())
    row = {'compound': comp, 'cells_union': len(union), 'in_all_3': len(common)}
    for d, s in sets.items():
        row[f'only_{d}'] = len(s - set.union(*[t for e, t in sets.items() if e != d]))
    col_rows.append(row)
compound_columns = pd.DataFrame(col_rows).set_index('compound')
compound_columns.to_csv(OUT / 'compound_columns.csv')
compound_columns
'''))

cells.append(code_cell('''
diff_rows = []
for comp, g in isa_cells.groupby('compound'):
    sets = {d: set(zip(x['activity_key'], x['visit'])) for d, x in g.groupby('disease')}
    common = set.intersection(*sets.values())
    for d, s in sorted(sets.items()):
        for key, visit in sorted(s - common):
            diff_rows.append({'compound': comp, 'disease': d, 'activity_key': key, 'visit': visit})
not_common = pd.DataFrame(diff_rows)
not_common.to_csv(OUT / 'compound_columns_not_common.csv', index=False)
not_common.groupby(['compound', 'disease', 'activity_key'])['visit'].apply(lambda v: ', '.join(sorted(v, key=visit_order))).to_frame()
'''))

cells.append(markdown_cell('''
## 8. Disease row: what do the ISAs of one disease state share that the master does not have?

Activity keys not in the master SoA, per disease state: in how many of the 4 ISAs they occur. Content common across the ISAs of one disease state is "common across these ISAs", not DSA content.
'''))

cells.append(code_cell('''
non_master = grid[grid['isa_mark'] & ~grid['in_master_soa']]
disease_rows = (non_master.groupby(['disease', 'activity_key'])['isa']
                .apply(lambda s: ', '.join(sorted(set(s)))).to_frame('isas'))
disease_rows['n_isas'] = disease_rows['isas'].str.count(',') + 1
disease_rows = disease_rows.reset_index()
by_key = disease_rows.groupby('activity_key')['disease'].nunique().rename('n_disease_states')
disease_rows = disease_rows.merge(by_key, on='activity_key')
disease_rows.to_csv(OUT / 'disease_rows_non_master.csv', index=False)
disease_rows[disease_rows['n_disease_states'] == 1].sort_values(['disease', 'activity_key'])
'''))

cells.append(markdown_cell('''
## 9. Statements that point beyond the master SoA

An ED override on an activity the master SoA does not have: the "CPMP SoA" it refers to cannot be the master SoA alone. Also: the stated additions and whether they name the DSA.
'''))

cells.append(code_cell('''
beyond = grid[(grid['kind'] == 'override_ed')][['isa', 'compound', 'disease', 'activity_key', 'master_mark', 'in_master_soa']]
beyond = beyond.sort_values(['compound', 'disease', 'activity_key'])
beyond.to_csv(OUT / 'override_ed_cells.csv', index=False)
beyond
'''))

cells.append(code_cell('''
added = grid[grid['addition_stated'] != ''].groupby(['isa', 'addition_stated', 'activity_key'])['visit'].apply(
    lambda v: ', '.join(sorted(v, key=visit_order))).to_frame()
added
'''))

cells.append(markdown_cell('''
## 10. Delegated activities: what the ISAs put in their place

The master hands post-randomization marks for these activities to the ISA. For each, the ISA visits with a mark (`–` = the ISA has no mark for the activity).
'''))

cells.append(code_cell('''
deleg = grid[grid['delegated_by_master'] & grid['isa_mark']]
deleg_view = deleg.groupby(['activity_key', 'compound', 'disease'])['visit'].apply(
    lambda v: ', '.join(sorted(v, key=visit_order))).unstack(['compound', 'disease']).fillna('–')
master_view = (pd.Series({k: ', '.join(sorted([v for a, v in master_marks if a == k], key=visit_order)) for k in sorted(DELEGATED_ACTS)},
                         name=('master', '')))
deleg_view = deleg_view.reindex(sorted(DELEGATED_ACTS)).fillna('–')
deleg_view.insert(0, ('master', ''), master_view)
deleg_view.to_csv(OUT / 'delegated_activities.csv')
deleg_view.T
'''))

cells.append(markdown_cell('''
## 11. Lab tables: from SoA rows to tests

An SoA row such as "Chemistry" is a panel; its tests are listed in the protocol's clinical laboratory tests appendix, not in the SoA. Two inputs:

- `lab_tests.csv`: the main "Clinical Laboratory Tests" table of the master (Appendix 2) and of each ISA (Appendix 1 or 2), transcribed from the page images and checked against the text layer (OA05: image-only page, visual only). Column header and bold sub-header as printed. Conditional tables (Thyroid Safety Follow-Up, systemic hypersensitivity event) and CCI-redacted rows are not in it; see the `note` column.
- `lab_to_activity.csv`: lab-table column → SoA row, sub-header → SoA row (replaces the column mapping for the tests under it), and test name → SoA row. A mapping counts only where the activity key is in that protocol's SoA.

Every ISA appendix states: "The master protocol CPMP describes tests that may be performed at additional times noted in the SoA for this ISA. This table describes tests unique for ISA …". Read as document-stated: an ISA panel row carries the master's tests for that panel plus the ISA's own.
'''))

cells.append(code_cell('''
lab = pd.read_csv('lab_tests.csv', dtype=str).fillna('')
lmap = pd.read_csv('lab_to_activity.csv', dtype=str).fillna('')
assert set(lmap['level']) <= {'column', 'subgroup', 'test'}
known_keys = {k for keys in ACT_KEYS.values() for k in keys}
unknown_keys = sorted(set(lmap['activity_key']) - known_keys)
assert not unknown_keys, f'mapping to keys not in any SoA: {unknown_keys}'
assert set(lab['nct_id']) == {MASTER} | set(isas['nct_id'])

COL_MAP = {r.column_header: r.activity_key for r in lmap[lmap['level'] == 'column'].itertuples()}
SUB_MAP = {(r.column_header, r.subgroup): r.activity_key for r in lmap[lmap['level'] == 'subgroup'].itertuples()}
TEST_MAP = lmap[lmap['level'] == 'test'].groupby('test_as_printed')['activity_key'].apply(list).to_dict()


def covering_rows(nct, column, subgroup, test):
    keys = []
    if subgroup and (column, subgroup) in SUB_MAP:
        keys.append(SUB_MAP[(column, subgroup)])
    elif column in COL_MAP:
        keys.append(COL_MAP[column])
    keys += TEST_MAP.get(test, [])
    return [k for k in dict.fromkeys(keys) if k in ACT_KEYS[nct]]


lab['isa'] = lab['nct_id'].map(dict(zip(studies['nct_id'], studies['isa'])))
lab['rows'] = [covering_rows(r.nct_id, r.column_header, r.subgroup, r.test_as_printed) for r in lab.itertuples()]
lab['n_rows'] = lab['rows'].str.len()
lab.assign(rows=lab['rows'].str.join(' | ')).drop(columns='note').to_csv(OUT / 'lab_coverage.csv', index=False)
lab.groupby(['isa', 'n_rows']).size().unstack(fill_value=0).rename(columns=lambda n: f'{n} SoA rows')
'''))

cells.append(markdown_cell('''
### Tests covered by more than one SoA row

A test listed inside a panel column whose name is also an SoA row of its own.
'''))

cells.append(code_cell('''
lab[lab['n_rows'] >= 2].assign(rows=lambda d: d['rows'].str.join(' | '))[
    ['isa', 'column_header', 'subgroup', 'test_as_printed', 'rows']]
'''))

cells.append(markdown_cell('''
### Tests with no SoA row

Listed in the lab table, but no SoA row in the same protocol covers them under the mapping.
'''))

cells.append(code_cell('''
lab[lab['n_rows'] == 0].groupby(['column_header', 'subgroup', 'test_as_printed'])['isa'].apply(
    lambda s: ', '.join(s)).to_frame('protocols')
'''))

cells.append(markdown_cell('''
## 12. Delegated activities at test level

For each activity the master delegates to the ISAs (section 10): where the ISA schedules it. "own row" = an SoA row with the same activity key, with the ISA visits marked; "ISA lab table: n" = number of tests in the ISA lab table that map to this row. "inside" = the ISA lab table lists the test under a panel column, with the visits marked for that panel row. `–` = neither.
'''))

cells.append(code_cell('''
def isa_visits(nct, key):
    g = grid[(grid['nct_id'] == nct) & (grid['activity_key'] == key) & grid['isa_mark']]
    return ', '.join(sorted(g['visit'], key=visit_order)) or 'no marks'


rows = []
for isa in isas.itertuples():
    il = lab[lab['nct_id'] == isa.nct_id]
    for key in sorted(DELEGATED_ACTS):
        parts = []
        if key in ACT_KEYS[isa.nct_id]:
            n_added = int(il['rows'].apply(lambda r: key in r).sum())
            parts.append(f'own row: {isa_visits(isa.nct_id, key)}' + (f' (ISA lab table: {n_added})' if n_added else ''))
        via = il[il['test_as_printed'].map(lambda t: key in TEST_MAP.get(t, []))]
        for r in via.itertuples():
            for row in r.rows:
                if row != key:
                    parts.append(f'{r.test_as_printed} inside {row}: {isa_visits(isa.nct_id, row)}')
        rows.append({'compound': isa.compound, 'disease': isa.disease, 'isa': isa.isa,
                     'delegated': key, 'in_isa': '; '.join(parts) or '–'})
deleg_tests = pd.DataFrame(rows)
deleg_tests.to_csv(OUT / 'delegated_test_level.csv', index=False)
deleg_tests.pivot_table(index='delegated', columns=['compound', 'disease'], values='in_isa', aggfunc='first')
'''))

cells.append(code_cell('''
master_lab = lab[lab['nct_id'] == MASTER]
master_panel_tests = (master_lab.assign(row=master_lab['rows'])
                      .explode('row').dropna(subset=['row'])
                      .groupby('row')['test_as_printed'].count().rename('master tests'))
master_panel_tests[master_panel_tests.index.isin(DELEGATED_ACTS)].to_frame()
'''))

cells.append(markdown_cell('''
## Outputs

`output/`: `layered_grid.csv` (one row per ISA × activity key × visit), `kinds_per_isa.csv`, `compound_columns.csv`, `compound_columns_not_common.csv`, `disease_rows_non_master.csv`, `override_ed_cells.csv`, `delegated_activities.csv`, `lab_coverage.csv`, `delegated_test_level.csv`.

Open points: the crosswalk and lab mapping proposals (`proposed`); the DSA layer, which stays unknown. "Post randomization" starts at the randomization event inside Visit 3 (master protocol: "All conditions existing prior to randomization at Visit 3 will be used as baseline"); the notebook applies delegation per activity, not per visit.
'''))

for i, c in enumerate(cells):
    c['id'] = f'cell-{i:02d}'

nb = {
    'cells': cells,
    'metadata': {
        'kernelspec': {'display_name': 'Python 3', 'language': 'python', 'name': 'python3'},
        'language_info': {'name': 'python'},
    },
    'nbformat': 4,
    'nbformat_minor': 5,
}
OUT.parent.mkdir(exist_ok=True)
with open(OUT, 'w', encoding='utf-8') as fh:
    json.dump(nb, fh, indent=1, ensure_ascii=False)
print('wrote', OUT, len(cells), 'cells')
