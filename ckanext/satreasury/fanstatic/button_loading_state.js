/**
 * On button click swaps out 'Finish' text in button on 'resource_form' page with 'Uploading' text
 * and adds an animated loading spinner. This indicates to the user that the file starts uploading
 * only once the 'Finish' button is pressed and not when the 'Upload' button is pressed and file is
 * selected.
 */
this.ckan.module('button_loading_state', function () {
  return {
    currentValue: false,
    options: {
      currentValue: null
    },
    initialize: function() {
      var button = this.el[0];
  
      if (!button) {
        return null;
      }
      
      function renderUploadingState() {
        button.innerHTML = '<span class="animated-loading-icon"></span><span>Uploading files</span>';
      }

      button.addEventListener('click', renderUploadingState)
    },
  };
});
