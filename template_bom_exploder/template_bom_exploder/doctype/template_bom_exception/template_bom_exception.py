import frappe
from frappe.model.document import Document


class TemplateBOMException(Document):
	def validate(self):
		if not self.exception_attributes:
			frappe.throw("At least one Exception Attribute is required.")
		if not self.exception_items:
			frappe.throw("At least one Exception Item is required.")
