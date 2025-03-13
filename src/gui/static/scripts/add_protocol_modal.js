// Open modal function accepting a callback
function openProtocolsModal(callback) {
	// Reset form fields
	$('#addProtocolForm')[0].reset();
	$('#protocolsModal').modal('show');
	$('#protocolsModal').on('shown.bs.modal', function () {
		$('#protocol_select').focus();
	});
	
	// Set up save button click
	$('#saveProtocolBtn').off('click').on('click', function() {
		// Construct IP from the four inputs
		var protocol = $('#protocol_select').val();
		
		$('#protocolsModal').modal('hide');
		if (callback && typeof callback === 'function') {
			callback(protocol);
		}
	});
}
