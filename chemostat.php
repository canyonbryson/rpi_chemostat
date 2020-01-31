

<?php
header('Content-Type: text/event-stream');
header('Cache-Control: no-cache');

temp = data('r');

we may need a separate file for each variable
OD = data;
sparging = data;


echo "temp: {temp}\n\n";
flush();
?>
