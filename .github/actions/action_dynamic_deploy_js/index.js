const core = require('@actions/core');
const github = require('@actions/github');
const axios = require('axios');

(function(){
    console.log(arguments);
    console.log("working in: "+__dirname);

    const eventFilePath = __dirname + "/../test.txt";
    fs.readFile(eventFilePath, function(err, fileData) {
        if (err) {
            throw err;
        }

        let config = {
            headers: {
                'Content-Type': 'application/json;charset=utf-8'
            }
        };

        axios.post(fileData, config).then((res) => {
            console.log("Response: ", res);
        }).catch((err) => {
            console.log("error: ", err);
        })
    });
})();



