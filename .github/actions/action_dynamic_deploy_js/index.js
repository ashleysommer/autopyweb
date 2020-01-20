const core = require('@actions/core');
const github = require('@actions/github');
const fs = require('fs');
const axios = require('axios');

async function main() {
    console.log(arguments);
    console.log();
    console.log("working in: " + __dirname);

    const event = JSON.parse(fs.readFileSync('/github/workflow/event.json', 'utf8'));
    let config = {
        headers: {
            'Content-Type': 'application/json;charset=utf-8'
        }
    };

    axios.post("http://example.org", event, config).then((res) => {
        console.log("Response: ", res);
    }).catch((err) => {
        console.log("error: ", err);
    });
    return "OK";
}
if (require.main === module) {
  main(process.argv)
    .then(res => {
      console.log({ res });
      process.exitCode = 0
    })
    .catch(err => {
      console.log({ err });
      process.exitCode = 1
    })
}

