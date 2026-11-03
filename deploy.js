const { NodeSSH } = require('node-ssh');
const fs = require('fs');
const path = require('path');
require('dotenv').config();

const ssh = new NodeSSH();

async function deploy() {
  try {
    const host = process.env.DEPLOY_HOST;
    const username = process.env.DEPLOY_USER || 'root';
    const password = process.env.DEPLOY_PASSWORD;
    const privateKey = process.env.DEPLOY_KEY_PATH ? fs.readFileSync(process.env.DEPLOY_KEY_PATH, 'utf8') : undefined;

    if (!host) {
      console.error('Error: Please provide DEPLOY_HOST in environment variables or .env');
      process.exit(1);
    }

    if (!password && !privateKey) {
      console.error('Error: Please provide DEPLOY_PASSWORD or DEPLOY_KEY_PATH in environment variables or .env');
      process.exit(1);
    }

    console.log(`Connecting to VPS (${host})...`);
    await ssh.connect({
      host,
      username,
      password,
      privateKey
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
      const localFilePath = path.join(__dirname, file);
      if (fs.existsSync(localFilePath)) {
        if (file === 'users.json' || file === 'bot_config.json') {
          // Never overwrite existing live databases on remote
          const checkRemote = await ssh.execCommand(`test -f ${remotePath}/${file} && echo "EXISTS"`);
          if (checkRemote.stdout.includes('EXISTS')) {
            console.log(`Preserving live remote ${file} (skipping upload)`);
            continue;
          }
        }
        await ssh.putFile(localFilePath, `${remotePath}/${file}`);
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
    // Kill existing screens and processes if running
    await ssh.execCommand('screen -S qr_bot -X quit; screen -S qrbot -X quit; pkill -f "/root/qr_bot/venv/bin/python main.py"');
    await new Promise((r) => setTimeout(r, 1500));
    
    // Start in screen qr_bot with supervisor loop
    result = await ssh.execCommand('screen -dmS qr_bot bash -c "cd /root/qr_bot && ulimit -n 65535 && while true; do ./venv/bin/python main.py 2>&1 | tee -a bot.log; echo \'[qr_bot] Bot stopped. Restarting in 5s...\'; sleep 5; done"', { cwd: remotePath });
    console.log('Start output:', result.stdout, result.stderr);

    console.log('Deployment complete!');
    process.exit(0);
  } catch (error) {
    console.error('Deployment failed:', error);
    process.exit(1);
  }
}

deploy();
