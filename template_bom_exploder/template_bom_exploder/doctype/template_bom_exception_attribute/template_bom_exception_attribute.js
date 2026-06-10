frappe.ui.form.on('Template BOM Exception Attribute', {
    attribute: function(frm, cdt, cdn) {
        let row = locals[cdt][cdn];
        frappe.model.set_value(cdt, cdn, 'attribute_value', '');
    }
});
