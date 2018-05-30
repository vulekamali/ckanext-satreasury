/* Dataset visibility toggler
 * When no organization is selected in the org dropdown then set visibility to
 * private and disable dropdown.
 * Default to Public when an organization is selected.
 */
this.ckan.module('satreasury_dataset_visibility', function ($, _) {
  return {
    currentValue: false,
    options: {
      currentValue: null
    },
    initialize: function() {
      $.proxyAll(this, /_on/);
      this.options.organizations = $('#field-organizations'),
      this.options.private_select_field = $('#field-private-select'),
      this.options.private_input_field = $('#field-private-input'),
      this.options.currentValue = this.options.private_select_field.val();
      this.options.organizations.on('change', this._onOrganizationChange);
      this._onOrganizationChange();
    },
    _onOrganizationChange: function() {
      var value = this.options.organizations.val();
      if (value) {
        this.options.private_select_field
          .prop('disabled', false)
          .val('False');
        this.options.private_input_field
          .prop('disabled', true);
      } else {
        this.options.private_select_field
          .prop('disabled', true)
          .val('True');
        this.options.private_input_field
          .prop('disabled', false);
      }
    }
  };
});
