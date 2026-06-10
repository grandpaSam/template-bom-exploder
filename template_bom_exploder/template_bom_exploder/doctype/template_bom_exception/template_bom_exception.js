frappe.ui.form.on("Template BOM Exception Attribute", {
	attribute: function (frm, cdt, cdn) {
		frappe.model.set_value(cdt, cdn, "attribute_value", "");
		const row = locals[cdt][cdn];
		if (!row.attribute) return;
		setup_exception_attribute_awesomplete(frm, cdt, cdn, row.attribute);
	},

	form_render: function (frm, cdt, cdn) {
		const row = locals[cdt][cdn];
		if (!row.attribute) return;
		setup_exception_attribute_awesomplete(frm, cdt, cdn, row.attribute);
	},
});

function setup_exception_attribute_awesomplete(frm, cdt, cdn, attribute) {
	frappe.call({
		method: "template_bom_exploder.template_bom_exploder.doctype.bom_attribute_compatibility.bom_attribute_compatibility.get_attribute_values",
		args: { attribute: attribute },
		callback: function (r) {
			if (!r.message) return;

			const grid_row = frm.fields_dict["exception_attributes"].grid.get_row(cdn);
			if (!grid_row || !grid_row.grid_form) return;

			const input = $(grid_row.grid_form.wrapper)
				.find('[data-fieldname="attribute_value"] input')
				.get(0);
			if (!input) return;

			// Destroy existing Awesomplete instance if present
			if (input.awesomplete) {
				input.awesomplete.destroy();
			}

			const awesomplete = new Awesomplete(input, {
				list: r.message,
				minChars: 0,
				autoFirst: true,
			});

			// Store reference on the element for cleanup on next call
			input.awesomplete = awesomplete;

			input.addEventListener("focus", function () {
				awesomplete.evaluate();
			});

			input.addEventListener("awesomplete-selectcomplete", function () {
				frappe.model.set_value(cdt, cdn, "attribute_value", input.value);
			});
		},
	});
}
