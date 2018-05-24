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
      this.options.visibility = $('#field-private-satreasury'),
      this.options.currentValue = this.options.visibility.val();
      this.options.organizations.on('change', this._onOrganizationChange);
      this._onOrganizationChange();
    },
    _onOrganizationChange: function() {
      var value = this.options.organizations.val();
      if (value) {
        this.options.visibility
          .prop('disabled', false)
          .val('False');
      } else {
        this.options.visibility
          .prop('disabled', true)
          .val('True');
      }
    }
  };
});
