const { NodeSSH } = require('node-ssh');
const fs = require('fs');
const path = require('path');

const ssh = new NodeSSH();

async function deploy() {
  try {
    console.log('Connecting to VPS...');
    await ssh.connect({
      host: '139.84.213.112',
      username: 'root',
      password: 'new_vps_paid'
    });
    console.log('Connected!');

    const remotePath = '/root/qr_bot';
    
    // Create directory
    await ssh.execCommand(`mkdir -p ${remotePath}`);

    const filesToUpload = [
      '.env',
      'bot_config.json',
      'font.ttf',
      'keep_alive.py',
      'main.py',
      'requirements.txt',
      'users.json'
    ];

    console.log('Uploading files...');
    for (const file of filesToUpload) {
      if (fs.existsSync(file)) {
        await ssh.putFile(path.join(__dirname, file), `${remotePath}/${file}`);
        console.log(`Uploaded ${file}`);
      }
    }

    console.log('Installing dependencies on VPS...');
    let result = await ssh.execCommand('apt-get update && apt-get install python3-pip python3-venv screen -y', { cwd: remotePath });
    console.log('Apt output:', result.stdout, result.stderr);

    result = await ssh.execCommand('python3 -m venv venv', { cwd: remotePath });
    console.log('Venv output:', result.stdout, result.stderr);

    result = await ssh.execCommand('./venv/bin/pip install -r requirements.txt', { cwd: remotePath });
    console.log('Pip output:', result.stdout, result.stderr);

    console.log('Starting bot...');
    // Kill existing screen if running
    await ssh.execCommand('screen -S qrbot -X quit');
    
    // Start in screen
    result = await ssh.execCommand('screen -dmS qrbot ./venv/bin/python main.py', { cwd: remotePath });
    console.log('Start output:', result.stdout, result.stderr);

    console.log('Deployment complete!');
    process.exit(0);
  } catch (error) {
    console.error('Deployment failed:', error);
    process.exit(1);
  }
}

deploy();
