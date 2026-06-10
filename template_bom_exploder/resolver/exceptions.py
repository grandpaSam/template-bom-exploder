import frappe


def apply_exceptions(resolved_items, target_attributes, template_bom_name):
	"""
	Applies Template BOM Exceptions to a resolved item list for a given BOM level.

	Called after resolve_bom_tree has built its resolved_items list for a level,
	before returning. At this point target_attributes are already compatibility-
	resolved, so we do direct dict matching only.

	Args:
		resolved_items:    list of resolved item dicts for this BOM level
		target_attributes: dict of attribute->value for the variant being built
		                   (already passed through compatibility resolution)
		template_bom_name: the template BOM name for this level — used to look up
		                   the template item and then fetch matching exception records

	Returns:
		modified resolved_items list with exceptions applied
	"""
	exception_records = _get_exceptions(template_bom_name)

	if not exception_records:
		return resolved_items

	for exception in exception_records:
		if not _attributes_match(exception['attributes'], target_attributes):
			continue

		replace_item = exception.get('replace_item')

		# Remove the replaced item if specified
		if replace_item:
			before_count = len(resolved_items)
			resolved_items = [
				item for item in resolved_items
				if (item.get('resolved_item_code') or item.get('item_code')) != replace_item
			]
			removed = before_count - len(resolved_items)
			if removed == 0:
				frappe.log_error(
					f"Template BOM Exception '{exception['name']}': replace_item '{replace_item}' "
					f"was not found in the resolved item list for BOM '{template_bom_name}' "
					f"with attributes {target_attributes}.",
					"TBE Exception Warning"
				)

		# Append the exception items
		for exc_item in exception['items']:
			resolved_items.append({
				**exc_item,
				'resolved_item_code': exc_item['item_code'],
				'resolved_item_name': exc_item.get('item_name') or exc_item['item_code'],
				'is_exception':       True,
				'exception_name':     exception['name'],
				'exception_replaces': replace_item or None,
			})

	return resolved_items


def _get_exceptions(template_bom_name):
	"""
	Fetches all Template BOM Exception records for the given BOM level.

	Resolves the BOM name to its item, then walks up to the template item
	if the BOM belongs to a variant. This ensures exceptions are found
	whether template_bom_name is a template BOM or a generated variant BOM.

	Returns a list of dicts:
		[
			{
				'name':         str,
				'replace_item': str | None,
				'attributes':   [{'attribute': str, 'attribute_value': str}, ...],
				'items':        [{ full exception item fields }, ...],
			},
			...
		]
	"""
	item_code = frappe.db.get_value('BOM', template_bom_name, 'item')
	if not item_code:
		return []

	# Walk up to the template item if this BOM belongs to a variant
	variant_of = frappe.db.get_value('Item', item_code, 'variant_of')
	template_item = variant_of or item_code

	exception_names = frappe.get_all(
		'Template BOM Exception',
		filters={'template_item': template_item},
		pluck='name',
	)

	if not exception_names:
		return []

	result = []
	for name in exception_names:
		doc = frappe.get_doc('Template BOM Exception', name)
		result.append({
			'name':         doc.name,
			'replace_item': doc.replace_item or None,
			'attributes': [
				{
					'attribute':       row.attribute,
					'attribute_value': row.attribute_value,
				}
				for row in doc.exception_attributes
			],
			'items': [
				{
					'item_code':                          row.item_code,
					'item_name':                          row.item_name,
					'qty':                                row.qty,
					'stock_qty':                          row.stock_qty,
					'uom':                                row.uom,
					'stock_uom':                          row.stock_uom,
					'conversion_factor':                  row.conversion_factor,
					'rate':                               row.rate,
					'amount':                             row.amount,
					'base_rate':                          row.base_rate,
					'base_amount':                        row.base_amount,
					'source_warehouse':                   row.source_warehouse,
					'include_item_in_manufacturing':      row.include_item_in_manufacturing,
					'custom_do_not_explode_for_template': row.custom_do_not_explode_for_template,
					'description':                        row.description,
				}
				for row in doc.exception_items
			],
		})

	return result


def _attributes_match(exception_attributes, target_attributes):
	"""
	Returns True if all rows in exception_attributes match target_attributes (AND logic).

	exception_attributes is a list of {'attribute': str, 'attribute_value': str}.
	target_attributes is the resolved dict from the resolver context.

	Compatibility resolution has already happened by the time we get here,
	so we do a direct value comparison only.
	"""
	for row in exception_attributes:
		attr  = row['attribute']
		value = row['attribute_value']

		if target_attributes.get(attr) == value:
			continue

		# No match found for this row — AND logic means the whole exception fails
		return False

	return True
