async function send_packet(packet_info){
    // TODO: use apipaths
    result = await fetchData('/monitoring/send/packet', 'POST', packet_info)
    packet_id = result['packet_id']

    // in loop, check if packet result is avaialble
    packet_result = null
    while(true){
        result = await fetchData('/monitoring/packet/' + packet_id, 'GET')
        console.log(result)
        if(result['status'] == 'completed'){
            packet_result = result
            break
        }
        await new Promise(r => setTimeout(r, 300));
    }

    if (packet_result != null){
        steps = []
        for(var i = 0; i < packet_result['steps'].length; i++){
            steps.push(packet_result['steps'][i]['id'])
        }
        animatePacketPath(steps)
    }
}

function openSendPacketModal(callback) {
	// Reset form fields
	$('#sendPacketForm')[0].reset();
	$('#sendPacketModal').modal('show');

	// on modal show, focus on the first input
	$('#sendPacketModal').on('shown.bs.modal', function() {
		$('#packet-protocol_select').focus();
	});

    // reset select options
    $('#packet-source_select').empty();
    $('#packet-dest_select').empty();

    $('#packet-source_select').append($('<option>', {
        value: '',
        text: '--- Select Source Host ---',
        disabled: true,
        selected: true
    }));

    $('#packet-dest_select').append($('<option>', {
        value: '',
        text: '--- Select Destination Host ---',
        disabled: true,
        selected: true
    }));

    // Load data in host source and destination from graph_data
    graph_data.nodes.forEach(element => {
        if (element.type === 'Host') {
            $('#packet-source_select').append($('<option>', {
                value: element.id,
                text: element.name
            }));
            $('#packet-dest_select').append($('<option>', {
                value: element.id,
                text: element.name
            }));
        }
    });
    
	
	// Set up save button click
	$('#sendPacketBtn').off('click').on('click', function() {

        var protocol = $('#packet-protocol_select').val();
		if (protocol === '' || protocol === null || protocol === undefined) {
			alert('Please select a protocol.');
			return;
		}
		var protocol = $('#packet-protocol_select').val();

		var port = $('#packet-port_input').val();
        if (port === '' || isNaN(port) || port < 1 || port > 65535) {
            alert('Please enter a valid port number between 1 and 65535.');
            return;
        }
		var port = $('#packet-port_input').val();

        var source = $('#packet-source_select').val();
        if (source === '' || source === null || source === undefined) {
            alert('Please select a source host.');
            return;
        }

        var dest = $('#packet-dest_select').val();
        if (dest === '' || dest === null || dest === undefined) {
            alert('Please select a destination host.');
            return;
        }

        packet_info = {
            "source": source,
            "dest": dest,
            "protocol": protocol,
            "port": port
        }

        console.log(packet_info)
		
		$('#sendPacketModal').modal('hide');
        send_packet(packet_info)
	});
}

document.addEventListener('DOMContentLoaded', function() {
    // add event listener to send packet button
    document.getElementById('send-packet-btn')?.addEventListener('click', function() {
        openSendPacketModal();
    });
});