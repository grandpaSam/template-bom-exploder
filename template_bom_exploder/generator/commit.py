import frappe
from frappe.model.mapper import get_mapped_doc

from template_bom_exploder.generator.dry_run import run_dry_run
from template_bom_exploder.resolver import data


def commit_variants(template_bom_name, variant_items, overwrite=False):
	"""
	Atomic commit phase: re-runs the dry-run resolver, then generates variant BOMs
	for the requested variant items.

	Args:
		template_bom_name: name of the root template BOM
		variant_items:     list of variant item codes to generate BOMs for
		overwrite:         if True, cancel existing submitted BOMs (or delete drafts)
		                   and create fresh. if False, skip variants that already
		                   have a default active BOM.

	Returns:
		{
			'status':         'ok' | 'failed' | 'partial',
			'created':        [...],  # list of BOM names created
			'skipped':        [...],  # list of variant item codes skipped
			'failed':         [...],  # list of {variant_item, reason} dicts
			'dry_run_failed': True | False,
		}
	"""
	# --- 1. Re-run dry run fresh to catch any changes since the preview ---
	report = run_dry_run(
		template_bom_name=template_bom_name,
		get_bom_items_fn=data.get_bom_items,
		get_template_bom_fn=data.get_template_bom,
		get_item_fn=data.get_item,
		get_variant_attributes_fn=data.get_variant_attributes,
		get_existing_variants_fn=data.get_existing_variants,
		get_compatibility_mappings_fn=data.get_compatibility_mappings,
	)

	# --- 2. Filter to requested variants only ---
	requested = set(variant_items)
	target_variants = [v for v in report['variants'] if v['variant_item'] in requested]

	# --- 3. Abort entirely if any target variant failed resolution ---
	# Nothing gets written if the re-run surfaces new errors.
	failed_resolution = [v for v in target_variants if v['status'] == 'failed']
	if failed_resolution:
		return {
			'status': 'failed',
			'created': [],
			'skipped': [],
			'failed': [
				{
					'variant_item': v['variant_item'],
					'reason': (v['error'] or {}).get('reason', 'Resolution failed'),
				}
				for v in failed_resolution
			],
			'dry_run_failed': True,
		}
	# --- 4. Check submit permission once for all variants ---
	can_submit = frappe.has_permission('BOM', 'submit')

	# --- 5. Commit each variant individually ---
	# Failures are isolated per variant — one failure does not abort the others.
	created = []
	skipped = []
	failed  = []

	for variant in target_variants:
		try:
			result = _commit_variant_bom(
				variant=variant,
				template_bom_name=template_bom_name,
				overwrite=overwrite,
				can_submit=can_submit,
			)
			if result['status'] == 'skipped':
				skipped.append(variant['variant_item'])
			else:
				created.append(result['bom_name'])
		except Exception as e:
			import traceback
			__import__('pprint').pprint(e)
			frappe.log_error(traceback.format_exc(), 'TBE Commit Error')
			frappe.db.rollback()
			failed.append({
				'variant_item': variant['variant_item'],
				'reason': str(e),
			})
	# --- 6. Build overall status ---
	if failed and not created and not skipped:
		overall = 'failed'
	elif failed:
		overall = 'partial'
	else:
		overall = 'ok'

	return {
		'status':         overall,
		'created':        created,
		'skipped':        skipped,
		'failed':         failed,
		'dry_run_failed': False,
	}


def _get_existing_default_bom(item_code):
	"""Returns {'name': ..., 'docstatus': ...} or None."""
	return frappe.db.get_value(
		'BOM',
		filters={
			'item':       item_code,
			'is_default': 1,
			'is_active':  1,
			'docstatus':  ['in', [0, 1]],
		},
		fieldname=['name', 'docstatus'],
		as_dict=True,
	)


def _insert_and_submit_bom(new_doc, can_submit):
	"""Inserts a BOM doc and submits it if the user has permission."""
	frappe.flags.mute_messages = True
	try:
		new_doc.insert(ignore_permissions=False)
		if can_submit:
			new_doc.submit()
		else:
			frappe.db.set_value('BOM', new_doc.name, 'is_default', 1)
	finally:
		frappe.flags.mute_messages = False


def _commit_variant_bom(variant, template_bom_name, overwrite, can_submit):
	"""
	Creates a single root variant BOM from a resolved variant entry.

	Depth-first: recursively creates all sub-assembly BOMs before
	inserting the root BOM so that every child exists before it is
	referenced by its parent.

	Args:
		variant:            a variant entry from the dry-run report (status must be 'ok')
		template_bom_name:  name of the root template BOM
		overwrite:          whether to replace an existing BOM
		can_submit:         whether the current user has BOM submit permission

	Returns:
		{'status': 'created', 'bom_name': '...'}
		{'status': 'skipped'}
	"""
	variant_item = variant['variant_item']

	# --- Check for an existing default active BOM for this variant ---
	existing_bom = _get_existing_default_bom(variant_item)

	if existing_bom:
		if not overwrite:
			return {'status': 'skipped'}

		if existing_bom.docstatus != 1:
			frappe.delete_doc('BOM', existing_bom.name, force=True)

	# --- Depth-first: create all sub-assembly BOMs before the root ---
	# We call _commit_sub_assembly_bom for every top-level node.
	# It recurses into children before creating itself, so the deepest
	# nodes are always created first. Non-variant leaf nodes return early
	# harmlessly via the variant_of guard inside the helper.
	for node in variant['resolved_tree']:
		_commit_sub_assembly_bom(
			node=node,
			overwrite=overwrite,
			can_submit=can_submit,
		)

	# --- Copy header fields and operations from the template BOM ---
	new_doc = _build_bom_doc(
		template_bom_name=template_bom_name,
		resolved_item_code=variant_item,
		resolved_item_name=variant['variant_item_name'],
		children=variant['resolved_tree'],
	)

	_insert_and_submit_bom(new_doc, can_submit)
	return {'status': 'created', 'bom_name': new_doc.name}


def _commit_sub_assembly_bom(node, overwrite, can_submit):
	"""
	Recursively creates a BOM for a resolved sub-assembly node, depth-first.

	Only creates a BOM if the resolved item is a template variant (has variant_of).
	Non-template sub-assemblies already have their own BOMs in ERPNext — we leave
	those untouched.

	Args:
		node:        a resolved tree node from the dry-run report
		overwrite:   whether to replace an existing BOM
		can_submit:  whether the current user has BOM submit permission
	"""
	# --- Recurse into children first (depth-first) ---
	# This ensures the deepest sub-assemblies are created before their parents.
	for child in node.get('children', []):
		_commit_sub_assembly_bom(
			node=child,
			overwrite=overwrite,
			can_submit=can_submit,
		)

	resolved_item_code = node.get('resolved_item_code') or node['item_code']

	# --- Only create a BOM for template variants ---
	# Non-template items already have their own BOMs — leave them alone.
	item = frappe.db.get_value(
		'Item',
		resolved_item_code,
		['variant_of', 'has_variants'],
		as_dict=True,
	)
	if not item or not item.get('variant_of'):
		return

	# --- Check for an existing default active BOM ---
	existing_bom = _get_existing_default_bom(resolved_item_code)

	if existing_bom:
		if not overwrite:
			return

		if existing_bom.docstatus != 1:
			frappe.delete_doc('BOM', existing_bom.name, force=True)

	# --- Find the template BOM to map from ---
	template_item = item['variant_of']
	template_bom = frappe.db.get_value(
		'BOM',
		filters={
			'item':       template_item,
			'is_default': 1,
			'is_active':  1,
			'docstatus':  1,
		},
		fieldname='name',
	)

	if not template_bom:
		return
	# --- Build and insert the BOM doc ---
	new_doc = _build_bom_doc(
		template_bom_name=template_bom,
		resolved_item_code=resolved_item_code,
		resolved_item_name=node.get('resolved_item_name') or resolved_item_code,
		children=node.get('children', []),
	)
	_insert_and_submit_bom(new_doc, can_submit)


def _build_bom_doc(template_bom_name, resolved_item_code, resolved_item_name, children):
	"""
	Builds a new BOM doc by mapping header fields and operations from the
	template BOM, then populating items from the resolved children list.

	BOM Item is intentionally excluded from the mapping — items are always
	populated from the resolver output so that BOM Attribute Compatibility
	resolution is respected. ERPNext's native mapping only does direct
	attribute matching and knows nothing about our compatibility table.

	Args:
		template_bom_name:   name of the template BOM to copy header/operations from
		resolved_item_code:  item code for the new BOM's finished good
		resolved_item_name:  item name for the new BOM's finished good
		children:            list of resolved tree nodes to use as BOM items

	Returns:
		an unsaved frappe BOM Doc ready for insert()
	"""
	new_doc = get_mapped_doc(
		'BOM',
		template_bom_name,
		{
			'BOM': {
				'doctype': 'BOM',
				'validation': {'docstatus': ['=', 1]},
				'field_no_map': [
					'name',
					'item',
					'item_name',
					'is_default',
					'is_active',
					'amended_from',
					'route',
				],
			},
			'BOM Operation': {
				'doctype': 'BOM Operation',
			},
			# BOM Item intentionally excluded
		},
	)

	new_doc.item       = resolved_item_code
	new_doc.item_name  = resolved_item_name
	new_doc.is_default = 1
	new_doc.is_active  = 1

	# Defensive clear — ensure no items leaked through the mapping
	new_doc.items = []

	# Populate items from resolved children (top level of this node only).
	# ERPNext explodes non-template sub-assembly BOMs automatically at
	# Work Order / MRP time — we do not recurse into grandchildren here.
	for child in children:
		new_doc.append('items', {
			'item_code': child['resolved_item_code'] or child['item_code'],
			'item_name': child.get('resolved_item_name') or child['resolved_item_code'],
			'qty':       child['qty'],
			'uom':       child.get('uom') or 'Nos',
		})

	return new_doc

