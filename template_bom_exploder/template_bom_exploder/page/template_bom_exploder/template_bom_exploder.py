import frappe
from template_bom_exploder.generator.dry_run import run_dry_run
from template_bom_exploder.resolver import data
from template_bom_exploder.generator.commit import commit_variants as _commit_variants
import json


@frappe.whitelist()
def get_dry_run_report(bom_name):
    """
    Runs the dry-run resolver for all existing variants of the root template item
    and returns a structured report for UI confirmation.

    Args:
        bom_name: name of the root template BOM (e.g. 'BOM-SHIRT-TEMPLATE-001')

    Returns:
        The report dict from run_dry_run(), serialisable to JSON.
    """
    return run_dry_run(
        template_bom_name=bom_name,
        get_bom_items_fn=data.get_bom_items,
        get_template_bom_fn=data.get_template_bom,
        get_item_fn=data.get_item,
        get_variant_attributes_fn=data.get_variant_attributes,
        get_existing_variants_fn=data.get_existing_variants,
        get_compatibility_mappings_fn=data.get_compatibility_mappings,
    )

@frappe.whitelist()
def commit_variants(bom_name, variant_items, overwrite=False):
	"""
	Commits variant BOMs for the given variant item codes.

	Args:
		bom_name:      the root template BOM name
		variant_items: JSON-encoded list of variant item codes to commit
		               e.g. '["SHIRT-RED-L", "SHIRT-BLUE-M"]'
		overwrite:     if True, replace existing BOMs via cancel+amend

	Returns:
		Result dict from commit.commit_variants()
	"""
	if isinstance(variant_items, str):
		variant_items = json.loads(variant_items)

	if isinstance(overwrite, str):
		overwrite = overwrite.lower() in ('1', 'true', 'yes')

	return _commit_variants(
		template_bom_name=bom_name,
		variant_items=variant_items,
		overwrite=overwrite,
	)

