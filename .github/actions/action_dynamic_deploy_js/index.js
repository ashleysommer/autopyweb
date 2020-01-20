const core = require('@actions/core');
const github = require('@actions/github');
const axios = require('axios');

async function main(argv) {
    let deploy_endpoint;
    let payload;
    try {
      deploy_endpoint = core.getInput('dynamic_deploy_endpoint');
      // Get the JSON webhook payload for the event that triggered the workflow
      payload = JSON.stringify(github.context.payload, undefined, 2)
    } catch (error) {
      core.setFailed(error.message);
      return;
    }
    console.log("working in: " + __dirname);
    console.log("event payload: \n"+payload);

    let config = {
        headers: {
            'Content-Type': 'application/json;charset=utf-8'
        }
    };
    try {
      let config = {
        headers: {
          'Content-Type': 'application/json;charset=utf-8'
        }
      };
      let resp = axios.post(deploy_endpoint, payload, config);
      let { data } = resp.data;
      console.log("response: "+data)
    } catch(error) {
      console.log("error: "+error);
      throw error;
    }
    return "OK";
}
if (require.main === module) {
  main(process.argv)
    .then(res => {
      console.log({ res });
      process.exitCode = 0;
      core.setOutput('success', "true");
    }).catch(err => {
      console.log({ err });
      core.setOutput('success', "false");
      core.setFailed(err);
      process.exitCode = 1;
    })
}

