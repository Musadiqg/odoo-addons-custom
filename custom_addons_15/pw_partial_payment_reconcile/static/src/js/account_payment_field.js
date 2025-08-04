odoo.define('pw_partial_payment_reconcile.account_payment', function (require) {
    let ShowPaymentLineWidget = require('account.payment').ShowPaymentLineWidget;

    ShowPaymentLineWidget.include({
        events: _.extend({}, ShowPaymentLineWidget.prototype.events, {
            'click .o_partial_button': '_onClickPartial',
        }),
        /**
         * @override
         * Open popup to edit applied amount when users click on Outstanding payment.
         * @param {Object} event
         * @private
         */
         _onClickPartial: function (event) {
            event.stopPropagation();
            event.preventDefault();
            var info = JSON.parse(this.value);
            var line_id = $(event.target).data('id') || false;
            this.do_action({
                type: 'ir.actions.act_window',
                res_model: 'partial.payment.wizard',
                views: [[false, 'form']],
                target: 'new',
                context: {'line_id': line_id, 'move_id': JSON.parse(this.value).move_id},
            });
         },
    });
    return ShowPaymentLineWidget;
});
