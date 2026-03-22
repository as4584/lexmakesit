@echo off
echo Deploying portfolio to lexmakesit.com...

set SERVER=lex@104.236.100.245
set WSL_REPO=\\wsl$\Ubuntu\root\studio\lexmakesit\frontend\portfolio

echo Copying templates...
scp -r %WSL_REPO%\templates\index.html %SERVER%:~/antigravity_bundle/apps/portfolio/templates/index.html

echo Copying static images...
scp -r %WSL_REPO%\static\images\ %SERVER%:~/antigravity_bundle/apps/portfolio/static/images/

echo Restarting container...
ssh %SERVER% "docker restart portfolio-web-1"

echo Done! Visit https://lexmakesit.com to confirm.
pause
