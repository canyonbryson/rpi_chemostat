document.addEventListener('DOMConetentLoaded', () => {
    
    // Connect to websocket
    var socket = io.connect(location.protocol + '//' + document.domain + ':' + location.port);
                            
    // When refreshing, refresh data
    socket.on('refreshing', dataList => {
        document.querySelector('#temp').innerHTML = dataList[0];
        document.querySelector('#OD').innerHTML = dataList[1];
        document.querySelector('#sparging').innerHTML = dataList[2];
        document.querySelector('#media_pump').innerHTML = dataList[3];
        });
    });
