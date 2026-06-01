frappe.pages["template-bom-exploder"].on_page_load = function (wrapper) {
	const page = frappe.ui.make_app_page({
		parent: wrapper,
		title: "Template BOM Exploder",
		single_column: true,
	});

	$(frappe.render_template("template_bom_exploder", {})).appendTo(page.body);
	frappe.dom.set_style(TBE_STYLES);

	wrapper.page_obj = new TemplateBomExploderPage(page);
};

frappe.pages["template-bom-exploder"].on_page_show = function (wrapper) {
	// route_options is cleared by Frappe before on_page_show fires.
	// Read the BOM name directly from the route instead.
	const route = frappe.get_route();
	// route = ['template-bom-exploder', 'BOM-NAME'] if passed as segment
	// Fall back to wrapper.current_bom if set by bom.js via a different mechanism
	const bom_name = route[1] || wrapper.current_bom || null;
	wrapper.page_obj.init(bom_name);
};

// ---------------------------------------------------------------------------
// Controller
// ---------------------------------------------------------------------------

class TemplateBomExploderPage {
	constructor(page) {
		this.page = page;

		// DOM shortcuts
		this.$page = $(".tbe-page");
		this.$loading = this.$page.find(".tbe-loading");
		this.$fatal = this.$page.find(".tbe-fatal-error");
		this.$summary = this.$page.find(".tbe-summary");
		this.$controls = this.$page.find(".tbe-controls");
		this.$treePanel = this.$page.find(".tbe-tree-panel");
		this.$footer = this.$page.find(".tbe-footer");
		this.$select = this.$page.find(".tbe-variant-select");
		this.$overwrite = this.$page.find(".tbe-overwrite-checkbox");

		// State
		this.report = null; // full dry-run report dict
		this.bom_name = null;
	}
	init(bom_name) {
		this.report = null;

		this.$loading.show();
		this.$fatal.hide();
		this.$summary.hide();
		this.$controls.hide();
		this.$treePanel.hide();
		this.$footer.hide();
		this.$select.empty();
		this.$treePanel.find(".tbe-tree--root").empty();

		if (bom_name) {
			this.bom_name = bom_name;
		}

		if (!this.bom_name) {
			this._showFatal("No BOM name provided. Open this page from the BOM Actions menu.");
			this._hideLoading();
			return;
		}

		this._bindButtons();
		this._runDryRun();
	}
	// -----------------------------------------------------------------------
	// Data
	// -----------------------------------------------------------------------

	_runDryRun() {
		this._showLoading();
		this.$footer.show();
		frappe.call({
			method: "template_bom_exploder.template_bom_exploder.page.template_bom_exploder.template_bom_exploder.get_dry_run_report",
			args: { bom_name: this.bom_name },
			callback: (r) => {
				this._hideLoading();
				if (r.exc || !r.message) {
					this._showFatal("Dry-run failed. Check the error log for details.");
					return;
				}
				this.report = r.message;
				this._render();
			},
			error: () => {
				this._hideLoading();
				this._showFatal("Could not reach the server. Please try again.");
			},
		});
	}

	// -----------------------------------------------------------------------
	// Rendering
	// -----------------------------------------------------------------------

	_render() {
		const report = this.report;

		if (!report.variants || report.variants.length === 0) {
			this._showFatal(
				`No existing variants found for the template BOM "${report.template_bom}". ` +
					"Create variants before exploding.",
			);
			return;
		}

		// Header
		const first = report.variants[0];
		const rootName = first.root_item_name || report.template_bom;
		const rootCode = first.root_item_code || report.template_bom;

		this.$page.find(".tbe-title-name").text(rootName);
		this.$page.find(".tbe-title-code").text(`(${rootCode})`);
		this.$page.find(".tbe-subtitle").text(report.template_bom);

		// Summary pills
		this.$page.find(".tbe-total-count").text(report.summary.total);
		this.$page.find(".tbe-ok-count").text(report.summary.ok);
		this.$page.find(".tbe-failed-count").text(report.summary.failed);
		this.$summary.show();

		// Variant dropdown
		this.$select.empty();
		report.variants.forEach((v) => {
			const label =
				v.status === "failed"
					? `⚠ ${v.variant_item_name || v.variant_item} (${v.variant_item})`
					: `${v.variant_item_name || v.variant_item} (${v.variant_item})`;
			this.$select.append($("<option>").val(v.variant_item).text(label));
		});
		this.$controls.show();

		// Show footer
		this.$footer.show();
		this._updateConfirmButtons();

		// Render first variant
		this._renderVariant(report.variants[0]);
		this.$treePanel.show();
	}

	_renderVariant(variant) {
		const $variantError = this.$treePanel.find(".tbe-variant-error");
		const $tree = this.$treePanel.find(".tbe-tree--root");

		$tree.empty();
		$variantError.hide();

		if (variant.status === "failed") {
			const err = variant.error || {};
			$variantError.find(".tbe-error-card-item").text(`Item: ${err.item_code || "unknown"}`);
			$variantError.find(".tbe-error-card-reason").text(err.reason || "Unknown error");

			const $cands = $variantError.find(".tbe-error-card-candidates");
			if (err.candidates && err.candidates.length) {
				$variantError
					.find(".tbe-error-card-candidates-list")
					.text(err.candidates.join(", "));
				$cands.show();
			} else {
				$cands.hide();
			}

			$variantError.show();
			return;
		}

		// Build tree
		(variant.resolved_tree || []).forEach((node) => {
			$tree.append(this._buildTreeNode(node));
		});
	}

	_buildTreeNode(node) {
		const hasChildren = node.children && node.children.length > 0;

		const $li = $(`<li class="tbe-node ${hasChildren ? "tbe-node--parent" : ""}"></li>`);

		// Row
		const $row = $(`<div class="tbe-node-row"></div>`);

		// Toggle (only for parents)
		if (hasChildren) {
			const $toggle = $(`<button class="tbe-toggle" aria-label="expand">▶</button>`);
			$toggle.on("click", () => {
				const $children = $li.children(".tbe-children");
				const expanded = $li.hasClass("tbe-node--expanded");
				if (expanded) {
					$li.removeClass("tbe-node--expanded");
					$toggle.text("▶");
					$children.slideUp(150);
				} else {
					$li.addClass("tbe-node--expanded");
					$toggle.text("▼");
					$children.slideDown(150);
				}
			});
			$row.append($toggle);
		} else {
			$row.append($(`<span class="tbe-toggle tbe-toggle--leaf">•</span>`));
		}

		// Template side
		const $from = $(`
			<span class="tbe-node-item tbe-node-item--template">
				<span class="tbe-item-name">${frappe.utils.escape_html(node.item_name || node.item_code)}</span>
				<span class="tbe-item-code">(${frappe.utils.escape_html(node.item_code)})</span>
			</span>
		`);

		// Arrow
		const $arrow = $(`<span class="tbe-node-arrow">→</span>`);

		// Resolved side
		const resolvedName = node.resolved_item_name || node.resolved_item_code;
		const $to = $(`
			<span class="tbe-node-item tbe-node-item--resolved">
				<span class="tbe-item-name">${frappe.utils.escape_html(resolvedName)}</span>
				<span class="tbe-item-code">(${frappe.utils.escape_html(node.resolved_item_code)})</span>
			</span>
		`);

		// Qty + UOM badge
		const $qty = $(`
			<span class="tbe-node-qty">${node.qty} ${frappe.utils.escape_html(node.uom || "")}</span>
		`);

		$row.append($from, $arrow, $to, $qty);
		$li.append($row);

		// Children (collapsed by default)
		if (hasChildren) {
			const $childList = $(`<ul class="tbe-children"></ul>`).hide();
			node.children.forEach((child) => {
				$childList.append(this._buildTreeNode(child));
			});
			$li.append($childList);
		}

		return $li;
	}

	// -----------------------------------------------------------------------
	// Confirm buttons
	// -----------------------------------------------------------------------

	_updateConfirmButtons() {
		if (!this.report) return;

		const anyFailed = this.report.summary.failed > 0;

		// "Confirm Selected" is active as long as the selected variant is ok
		const selectedVariant = this._getSelectedVariant();
		const selectedOk = selectedVariant && selectedVariant.status === "ok";
		this.$footer.find(".tbe-btn-confirm-selected").prop("disabled", !selectedOk);

		// "Confirm All" only active if zero failures
		this.$footer.find(".tbe-btn-confirm-all").prop("disabled", anyFailed);

		if (anyFailed) {
			this.$footer
				.find(".tbe-btn-confirm-all")
				.attr(
					"title",
					"Cannot confirm all: one or more variants failed resolution. Fix the errors and re-run.",
				);
		} else {
			this.$footer.find(".tbe-btn-confirm-all").removeAttr("title");
		}
	}

	_getSelectedVariant() {
		const selectedCode = this.$select.val();
		if (!this.report) return null;
		return this.report.variants.find((v) => v.variant_item === selectedCode) || null;
	}

	// -----------------------------------------------------------------------
	// Button bindings
	// -----------------------------------------------------------------------

	_bindButtons() {
		// Variant selector change
		this.$select.on("change", () => {
			const variant = this._getSelectedVariant();
			if (variant) {
				this._renderVariant(variant);
				this._updateConfirmButtons();
			}
		});

		// Cancel — back to the BOM
		this.$page.on("click", ".tbe-btn-cancel", () => {
			frappe.set_route("Form", "BOM", this.bom_name);
		});

		// Confirm Selected
		this.$page.on("click", ".tbe-btn-confirm-selected", () => {
			const variant = this._getSelectedVariant();
			if (!variant || variant.status !== "ok") return;
			this._confirmVariants([variant.variant_item], false);
		});

		// Confirm All
		this.$page.on("click", ".tbe-btn-confirm-all", () => {
			if (!this.report) return;
			console.log('test')
			const okVariants = this.report.variants
				.filter((v) => v.status === "ok")
				.map((v) => v.variant_item);
			this._confirmVariants(okVariants, true);
		});
	}

	_confirmVariants(variantItems, isAll) {
		const overwrite = this.$overwrite.is(":checked");
		const label = isAll
			? `Generate BOMs for all ${variantItems.length} variants?`
			: `Generate BOM for ${variantItems[0]}?`;

		frappe.confirm(label, () => {
			// Disable buttons during commit
			this.$footer.find("button").prop("disabled", true);

			frappe.call({
				method: "template_bom_exploder.template_bom_exploder.page.template_bom_exploder.template_bom_exploder.commit_variants",
				args: {
					bom_name: this.bom_name,
					variant_items: JSON.stringify(variantItems),
					overwrite: overwrite ? "true" : "false",
				},
				freeze: true,
				freeze_message: isAll ? "Generating BOMs…" : "Generating BOM…",
				callback: (r) => {
					if (r.exc || !r.message) {
						frappe.msgprint({
							title: __("Error"),
							message: __("BOM generation failed. Check the error log."),
							indicator: "red",
						});
						this._updateConfirmButtons();
						return;
					}

					const result = typeof r.message === 'string' ? JSON.parse(r.message) : r.message;

					if (result.dry_run_failed) {
						frappe.msgprint({
							title: __("Resolution Changed"),
							message: __(
								"The resolver re-run found errors that were not present " +
									"during the dry-run preview. This may mean variants, items, " +
									"or compatibility mappings changed since you ran the preview. " +
									"Please re-run the dry-run to see the current state.",
							),
							indicator: "red",
						});
						this._updateConfirmButtons();
						return;
					}

					// Build result summary message
					const lines = [];
					if (result.created.length) {
						lines.push(
							`<b>${result.created.length} BOM(s) created:</b><br>` +
								result.created.map((b) => `&nbsp;&nbsp;• ${b}`).join("<br>"),
						);
					}
					if (result.skipped.length) {
						lines.push(
							`<b>${result.skipped.length} skipped</b> (already had a BOM):<br>` +
								result.skipped.map((i) => `&nbsp;&nbsp;• ${i}`).join("<br>") +
								`<br><small>Enable "Overwrite existing BOMs" to replace them.</small>`,
						);
					}
					if (result.failed.length) {
						lines.push(
							`<b>${result.failed.length} failed:</b><br>` +
								result.failed
									.map((f) => `&nbsp;&nbsp;• ${f.variant_item}: ${f.reason}`)
									.join("<br>"),
						);
					}

					const indicator =
						result.status === "ok"
							? "green"
							: result.status === "partial"
								? "orange"
								: "red";
					setTimeout(() => {
						frappe.msgprint({
							title: __("BOM Generation Complete"),
							message: lines.join("<br><br>"),
							indicator: indicator,
						});
					}, 1000);
					// Disable confirm buttons — commit is done
					this.$footer.find(".tbe-btn-confirm-selected").prop("disabled", true);
					this.$footer.find(".tbe-btn-confirm-all").prop("disabled", true);
				},
			});
		});
	}

	// -----------------------------------------------------------------------
	// Helpers
	// -----------------------------------------------------------------------

	_showLoading() {
		this.$loading.show();
	}

	_hideLoading() {
		this.$loading.hide();
	}

	_showFatal(msg) {
		this.$fatal.find(".tbe-fatal-message").text(msg);
		this.$fatal.show();
	}
}

// ---------------------------------------------------------------------------
// Styles — injected once on page load
// ---------------------------------------------------------------------------

const TBE_STYLES = `
/* ---- Layout ---- */
.tbe-page {
	display: flex;
	flex-direction: column;
	gap: 0;
	padding: 0 0 80px 0;
	min-height: 100%;
}

/* ---- Header ---- */
.tbe-header {
	display: flex;
	align-items: flex-start;
	justify-content: space-between;
	flex-wrap: wrap;
	gap: 12px;
	padding: 20px 24px 16px;
	border-bottom: 1px solid var(--border-color);
	background: var(--card-bg);
}

.tbe-header-left {
	display: flex;
	flex-direction: column;
	gap: 2px;
}

.tbe-title {
	font-size: 1.25rem;
	font-weight: 600;
	color: var(--heading-color);
	margin: 0;
	display: flex;
	align-items: baseline;
	gap: 6px;
}

.tbe-title-code {
	font-size: 0.85rem;
	font-weight: 400;
	color: var(--text-muted);
}

.tbe-subtitle {
	font-size: 0.8rem;
	color: var(--text-muted);
	margin: 0;
}

/* ---- Summary pills ---- */
.tbe-summary {
	display: flex;
	gap: 8px;
	align-items: center;
}

.tbe-pill {
	display: flex;
	flex-direction: column;
	align-items: center;
	justify-content: center;
	min-width: 56px;
	padding: 6px 12px;
	border-radius: 6px;
	border: 1px solid var(--border-color);
	background: var(--control-bg);
}

.tbe-pill-count {
	font-size: 1.1rem;
	font-weight: 700;
	line-height: 1;
}

.tbe-pill-label {
	font-size: 0.65rem;
	text-transform: uppercase;
	letter-spacing: 0.05em;
	color: var(--text-muted);
	margin-top: 2px;
}

.tbe-pill--ok   .tbe-pill-count { color: var(--green-500, #28a745); }
.tbe-pill--failed .tbe-pill-count { color: var(--red-500, #dc3545); }

/* ---- Controls ---- */
.tbe-controls {
	padding: 14px 24px;
	border-bottom: 1px solid var(--border-color);
	background: var(--card-bg);
	display: flex;
	align-items: center;
	gap: 12px;
}

.tbe-select-wrap {
	display: flex;
	align-items: center;
	gap: 8px;
}

.tbe-select-label {
	font-size: 0.8rem;
	font-weight: 500;
	color: var(--text-muted);
	white-space: nowrap;
	margin: 0;
}

.tbe-controls .form-control {
	width: 360px;
	max-width: 100%;
	font-size: 0.875rem;
}

/* ---- Loading ---- */
.tbe-loading {
	display: flex;
	flex-direction: column;
	align-items: center;
	justify-content: center;
	gap: 12px;
	padding: 60px 24px;
	color: var(--text-muted);
	font-size: 0.875rem;
}

.tbe-spinner {
	width: 28px;
	height: 28px;
	border: 3px solid var(--border-color);
	border-top-color: var(--primary);
	border-radius: 50%;
	animation: tbe-spin 0.7s linear infinite;
}

.tbe-overwrite-wrap {
    display: flex;
    align-items: center;
    margin-left: 16px;
}

.tbe-overwrite-label {
    display: flex;
    align-items: center;
    gap: 6px;
    font-size: 0.8rem;
    color: var(--text-muted);
    cursor: pointer;
    margin: 0;
    user-select: none;
}

.tbe-overwrite-checkbox {
    cursor: pointer;
    margin: 0;
}


@keyframes tbe-spin {
	to { transform: rotate(360deg); }
}

/* ---- Fatal error ---- */
.tbe-fatal-error {
	display: flex;
	align-items: center;
	gap: 10px;
	margin: 24px;
	padding: 14px 18px;
	background: var(--alert-bg, #fff3cd);
	border: 1px solid var(--yellow-200, #ffc107);
	border-radius: 6px;
	color: var(--text-color);
	font-size: 0.875rem;
}

.tbe-fatal-icon {
	font-size: 1.1rem;
	flex-shrink: 0;
}

/* ---- Tree panel ---- */
.tbe-tree-panel {
	flex: 1;
	padding: 20px 24px;
	overflow-y: auto;
}

/* ---- Variant error card ---- */
.tbe-variant-error {
	margin-bottom: 16px;
}

.tbe-error-card {
	border: 1px solid var(--red-200, #f5c6cb);
	background: var(--red-50, #fff5f5);
	border-radius: 6px;
	padding: 14px 18px;
	display: flex;
	flex-direction: column;
	gap: 6px;
	font-size: 0.875rem;
}

.tbe-error-card-title {
	font-weight: 600;
	color: var(--red-600, #c82333);
	font-size: 0.9rem;
}

.tbe-error-card-item {
	color: var(--text-muted);
	font-size: 0.8rem;
}

.tbe-error-card-reason {
	color: var(--text-color);
}

.tbe-error-card-candidates {
	font-size: 0.8rem;
	color: var(--text-muted);
}

.tbe-error-card-candidates-label {
	font-weight: 500;
	margin-right: 4px;
}

/* ---- Tree ---- */
.tbe-tree,
.tbe-children {
	list-style: none;
	padding: 0;
	margin: 0;
}

.tbe-tree--root > .tbe-node {
	border-bottom: 1px solid var(--border-color);
}

.tbe-node {
	padding: 0;
}

.tbe-children {
	padding-left: 32px;
	border-left: 2px solid var(--border-color);
	margin-left: 14px;
}

.tbe-children > .tbe-node {
	border-bottom: 1px solid var(--border-color);
}

.tbe-children > .tbe-node:last-child {
	border-bottom: none;
}

.tbe-node-row {
	display: flex;
	align-items: center;
	gap: 8px;
	padding: 8px 4px;
	min-height: 38px;
}

/* ---- Toggle button ---- */
.tbe-toggle {
	background: none;
	border: none;
	padding: 0;
	width: 18px;
	height: 18px;
	display: flex;
	align-items: center;
	justify-content: center;
	font-size: 0.6rem;
	color: var(--text-muted);
	cursor: pointer;
	flex-shrink: 0;
	transition: color 0.15s;
}

.tbe-toggle:hover {
	color: var(--primary);
}

.tbe-toggle--leaf {
	cursor: default;
	font-size: 0.5rem;
}

/* ---- Node items ---- */
.tbe-node-item {
	display: inline-flex;
	align-items: baseline;
	gap: 4px;
}

.tbe-item-name {
	font-weight: 500;
	color: var(--text-color);
	font-size: 0.875rem;
}

.tbe-item-code {
	font-size: 0.75rem;
	color: var(--text-muted);
	font-family: var(--monospace-font, monospace);
}

.tbe-node-item--resolved .tbe-item-name {
	color: var(--primary);
}

.tbe-node-arrow {
	color: var(--text-muted);
	font-size: 0.8rem;
	flex-shrink: 0;
	padding: 0 2px;
}

/* ---- Qty badge ---- */
.tbe-node-qty {
	margin-left: auto;
	font-size: 0.75rem;
	color: var(--text-muted);
	background: var(--control-bg);
	border: 1px solid var(--border-color);
	border-radius: 4px;
	padding: 1px 7px;
	white-space: nowrap;
	flex-shrink: 0;
}

/* ---- Footer ---- */
.tbe-footer {
	position: fixed;
	bottom: 0;
	left: 0;
	right: 0;
	display: flex;
	align-items: center;
	justify-content: space-between;
	padding: 12px 24px;
	background: var(--card-bg);
	border-top: 1px solid var(--border-color);
	box-shadow: 0 -2px 8px rgba(0,0,0,0.06);
	z-index: 100;
}

.tbe-footer-right {
	display: flex;
	gap: 8px;
}
`;
