frappe.ui.form.on("BOM", {
	refresh(frm) {
		// Only show on submitted, active, default BOMs for template items
		if (frm.doc.docstatus !== 1) return;
		if (!frm.doc.is_active) return;

		// Check if the BOM's item is a template item (has_variants)
		if (!frm.doc.item) return;

		frappe.db.get_value("Item", frm.doc.item, "has_variants", (r) => {
			if (!r || !r.has_variants) return;

			frm.add_custom_button(
				__("Explode Template BOM"),
				() => {
					frappe.set_route("template-bom-exploder", frm.doc.name);
				},
				__("Actions"),
			);
		});
	},
});
