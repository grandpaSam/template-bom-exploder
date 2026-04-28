// Copyright (c) 2026, Shawn Bero and contributors
// // For license information, please see license.txt
//
// // frappe.ui.form.on("BOM Attribute Compatibility", {
// //	refresh(frm) {
//
// //	},
// // });
// //
frappe.ui.form.on("BOM Attribute Compatibility", {
	source_attribute: function (frm) {
		frm.set_value("source_value", "");
		setup_awesomplete(frm, "source_attribute", "source_value");
	},
	target_attribute: function (frm) {
		frm.set_value("target_value", "");
		setup_awesomplete(frm, "target_attribute", "target_value");
	},
});

function setup_awesomplete(frm, attribute_field, value_field) {
	const attribute = frm.doc[attribute_field];
	if (!attribute) return;

	frappe.call({
		method: "template_bom_exploder.template_bom_exploder.doctype.bom_attribute_compatibility.bom_attribute_compatibility.get_attribute_values",
		args: { attribute: attribute },
		callback: function (r) {
			if (!r.message) return;

			const input = frm.fields_dict[value_field].input;

			// Destroy existing Awesomplete instance
			if (input.awesomplete) {
				input.awesomplete.destroy();
			}

			// Remove old listeners by replacing the element with a clone
			const new_input = input.cloneNode(true);
			input.parentNode.replaceChild(new_input, input);

			const awesomplete = new Awesomplete(new_input, {
				list: r.message,
				minChars: 0,
				autoFirst: true,
			});

			new_input.addEventListener("focus", function () {
				awesomplete.evaluate();
			});

			new_input.addEventListener("input", function () {
				awesomplete.evaluate();
			});

			new_input.addEventListener("awesomplete-selectcomplete", function () {
				new_input.dispatchEvent(new Event("change"));
				frm.set_value(value_field, new_input.value);
			});

			// Re-point frappe's field reference to the new input
			frm.fields_dict[value_field].input = new_input;
		},
	});
}
