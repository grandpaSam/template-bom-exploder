import frappe


def get_bom_items(bom_name):
	"""Returns list of raw materials from a BOM"""
	return frappe.get_all(
		'BOM Item',
		filters={'parent': bom_name, 'parenttype': 'BOM'},
		fields=['item_code', 'item_name', 'qty', 'uom', 'do_not_explode'],
		order_by='idx asc'
	)


def get_template_bom(item_code):
	"""Returns the default submitted BOM name for a given item code"""
	bom = frappe.db.get_value(
		'BOM',
		filters={
			'item': item_code,
			'is_default': 1,
			'is_active': 1,
			'docstatus': 1
		},
		fieldname='name'
	)
	return bom


def get_item(item_code):
	"""Returns key fields from an Item record"""
	return frappe.db.get_value(
		'Item',
		item_code,
		['item_code', 'item_name', 'variant_of', 'has_variants'],
		as_dict=True
	)


def get_variant_attributes(template_item_code):
	"""Returns list of attribute names for a template item"""
	attrs = frappe.get_all(
		'Item Variant Attribute',
		filters={'parent': template_item_code},
		fields=['attribute'],
		order_by='idx asc'
	)
	return [a.attribute for a in attrs]


def get_existing_variants(template_item_code):
	"""
	Returns all existing variants of a template item as a list of dicts:
	[
		{
			'item_code': 'LTEBK0009',
			'attributes': {'Caliber-ASR': '9mm', 'Color-ASR': 'Black'}
		},
		...
	]
	"""
	variants = frappe.get_all(
		'Item',
		filters={'variant_of': template_item_code},
		fields=['item_code']
	)

	result = []
	for variant in variants:
		attrs = frappe.get_all(
			'Item Variant Attribute',
			filters={'parent': variant.item_code},
			fields=['attribute', 'attribute_value']
		)
		result.append({
			'item_code': variant.item_code,
			'attributes': {a.attribute: a.attribute_value for a in attrs}
		})

	return result


def get_compatibility_mappings():
	"""
	Returns all BOM Attribute Compatibility records as a lookup structure:
	{
		(target_attribute, target_value): [
			{'source_attribute': ..., 'source_value': ...},
			...
		]
	}
	"""
	records = frappe.get_all(
		'BOM Attribute Compatibility',
		fields=['source_attribute', 'source_value', 'target_attribute', 'target_value']
	)

	mapping = {}
	for r in records:
		key = (r.target_attribute, r.target_value)
		if key not in mapping:
			mapping[key] = []
		mapping[key].append({
			'source_attribute': r.source_attribute,
			'source_value': r.source_value
		})

	return mapping
