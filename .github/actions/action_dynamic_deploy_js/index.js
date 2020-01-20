const core = require('@actions/core');
const github = require('@actions/github');
const axios = require('axios');

function process_pull_request(event) {
    let pr_id = event['number'];
    let pr = event['pull_request'];
    let action = event['action']; //open or synchronize
    let base = event['base']; // this is the dst branch of the PR
    let head = event['head']; // this is the src branch of the PR

}

async function main(argv) {
    let deploy_endpoint;
    let event, eventName;
    try {
      deploy_endpoint = core.getInput('dynamic_deploy_endpoint');
      // Get the JSON webhook payload for the event that triggered the workflow
      event = JSON.stringify(github.context.payload, undefined, 2);
      eventName = github.context.eventName;
    } catch (error) {
      core.setFailed(error.message);
      return;
    }
    console.log("working in: " + __dirname);
    console.log("event name: "+eventName);
    console.log("event payload: \n"+event);

    if (eventName === "pull_request") {
        return process_pull_request(event);
    }

    try {
      let deploy_post_endpoint = deploy_endpoint + "/add";
      let config = {
        headers: {
          'Content-Type': 'application/json;charset=utf-8'
        }
      };
      let resp = await axios.post(deploy_post_endpoint, event, config);
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

