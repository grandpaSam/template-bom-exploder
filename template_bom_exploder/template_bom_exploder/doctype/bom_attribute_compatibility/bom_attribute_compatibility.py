# Copyright (c) 2026, Shawn Bero and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document
from frappe import _



class BOMAttributeCompatibility(Document):
	def validate(self):
		self.validate_attribute_value('source_attribute', 'source_value')
		self.validate_attribute_value('target_attribute', 'target_value')
		self.validate_attributes_not_same()

	def validate_attribute_value(self, attribute_field, value_field):
		attribute = self.get(attribute_field)
		value = self.get(value_field)

		if not attribute or not value:
			return

		exists = frappe.db.exists('Item Attribute Value', {
			'parent': attribute,
			'attribute_value': value
		})

		if not exists:
			frappe.throw(
				_('"{0}" is not a valid value for attribute {1}').format(
					value, attribute
				)
			)
	def validate_attributes_not_same(self):
		if self.source_attribute == self.target_attribute:
			frappe.throw(
				_('Source Attribute and Target Attribute cannot be the same')
			)


@frappe.whitelist()
def get_attribute_values(attribute):
	values = frappe.get_all(
		'Item Attribute Value',
		filters={'parent': attribute},
		fields=['attribute_value'],
		order_by='idx asc'
	)
	return [v.attribute_value for v in values]

