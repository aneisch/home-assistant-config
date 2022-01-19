const webhook_host = "FQDN"
const webhook_location = "SECRET_WEBHOOK_ID"
const webhook_url= `https://${webhook_host}/api/webhook/${webhook_location}`

addEventListener("fetch", event => {
  event.respondWith(handleRequest(event.request))
})

function generateRandomNumber() {
    var minm = 100000;
    var maxm = 999999;
    return Math.floor(Math
    .random() * (maxm - minm + 1)) + minm;
}

async function handleRequest(request) {
  let url = new URL(request.url);
  let path = url.pathname;
  let requestHeaders = Object.fromEntries(request.headers)
  // Generate OTP
  email = requestHeaders["cf-access-authenticated-user-email"] || "unknown"

  if (path.includes("get-otp")) {
    otp = generateRandomNumber()
    
    body = {
      "otp": otp,
      "email": email
    }

    // Add code to lock
    const init = {
      body: JSON.stringify(body),
      method: "POST",
      headers: {
        "content-type": "application/json;charset=UTF-8",
      },
    }
    const response = await fetch(webhook_url, init)

    html = `<!DOCTYPE html>
    <head>
    <link rel="stylesheet" href="https://maxcdn.bootstrapcdn.com/bootstrap/3.4.1/css/bootstrap.min.css">
    <script>
    var timeleft = 30;
    var downloadTimer = setInterval(function(){
      if(timeleft <= 0){
        clearInterval(downloadTimer);
      document.getElementById("message").innerHTML = "<h1>Your code has expired. Refresh to get a new one</h1>"
      }
      document.getElementById("time").innerHTML = timeleft;
      timeleft -= 1;
      }, 1000);
    </script>
    </head>
    <body>
      <center>
      <span style="font-size:8vw;" id=message>Your one time unlock code is <span id=code><strong>${otp}</strong></span><br><br>Use it at the garage exterior door behind the gate.<br><br><span id=remain>This code will expire in <span id=time>30</span> seconds</span>.</span>
      </center>
    </body>`
  }

  else {
    html = `<!DOCTYPE html>
    <head>
    <link rel="stylesheet" href="https://maxcdn.bootstrapcdn.com/bootstrap/3.4.1/css/bootstrap.min.css">
    </head>
    <body>
      <center>
      <span style="font-size:8vw;" id=message>Hi ${requestHeaders["cf-access-authenticated-user-email"]}, tap below to get your code.</span><br><br><br>
      <button style="font-size:6vw;" class="btn btn-primary btn-lg" onclick="window.location.href = './get-otp'">Get OTP</button>
      </center>
    </body>`
  }

  return new Response(html, {
    headers: {
      "content-type": "text/html;charset=UTF-8",
    },
  })
}
