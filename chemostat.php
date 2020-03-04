<?php

from chemostat_code.py import OD

header('Content-Type: text/event-stream');
header('Cache-Control: no-cache');

OD = OD();


echo "OD: {OD}\n\n";
flush();
?>
