#!/usr/bin/env node

var http = require('http');
var connect = require('connect');
var serveStatic = require('serve-static');
var morgan = require('morgan');
var path = require('path');

// ENV
require('dotenv').config()

var app = connect();

app.use(morgan('dev'));
app.use('/', serveStatic(path.join(__dirname, 'app')));

const port = process.env.PORT;
app.listen(port);

console.log('Server listening on port', port);
