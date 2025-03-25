// Open modal function accepting a callback
function openProtocolsModal(callback, protocols) {
	// Reset form fields
	$('#addProtocolForm')[0].reset();
	$('#protocolsModal').modal('show');
	$('#protocolsModal').on('shown.bs.modal', function () {
		$('#protocol_select').focus();
	});
	
	// Set up save button click
	$('#saveProtocolBtn').off('click').on('click', function() {
		// Check if protocol is valid
		var protocol = $('#protocol_select').val();
		if (protocol === '' || protocol === null || protocol === undefined) {
			alert('Please select a protocol.');
			return;
		}
		if (protocols.includes(protocol)) {
			alert('This protocol is already in use.');
			return;
		}
		var protocol = $('#protocol_select').val();
		
		$('#protocolsModal').modal('hide');
		if (callback && typeof callback === 'function') {
			callback(protocol);
		}
	});
}
