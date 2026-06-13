let mediaStream=null,audioContext=null,analyserNode=null,loopbackActive=false,animationId=null;
let mediaRecorder=null,recordedChunks=[],profileName=null,liveAnalyser=null,liveAnimationId=null;
let calibrationData={noise_db:null,noise_level:null,noise_advice:null,wer:null,transcribed:null,test_phrase_original:null,steps_completed:[]};

async function loadProfileName(){
    try{
        const r=await fetch('/api/profile');
        if(r.ok){
            const d=await r.json();
            profileName=d.name;
            document.getElementById('testPhrase').innerHTML='My name is '+profileName+'. I am learning English.';
            calibrationData.test_phrase_original='My name is '+profileName+'. I am learning English.';
        }else{
            profileName='Student';
            document.getElementById('testPhrase').innerHTML='My name is [Your Name]. I am learning English.';
        }
    }catch(e){profileName='Student';}
}

async function getAudioStream(){
    try{return await navigator.mediaDevices.getUserMedia({audio:true});}
    catch(e){alert('No microphone access');return null;}
}

function stopAllAudio(){
    if(loopbackActive)stopLoopback();
    if(mediaStream){mediaStream.getTracks().forEach(t=>t.stop());mediaStream=null;}
}
async function startLoopback(){
    if(loopbackActive)stopLoopback();
    mediaStream=await getAudioStream();
    if(!mediaStream)return;
    audioContext=new AudioContext();
    const source=audioContext.createMediaStreamSource(mediaStream);
    analyserNode=audioContext.createAnalyser();
    source.connect(audioContext.destination);
    source.connect(analyserNode);
    loopbackActive=true;
    document.getElementById('loopbackBtn').disabled=true;
    document.getElementById('stopLoopbackBtn').disabled=false;
    updateVolumeIndicator();
}

function stopLoopback(){
    if(audioContext)audioContext.close();
    if(mediaStream)mediaStream.getTracks().forEach(t=>t.stop());
    loopbackActive=false;
    if(animationId)cancelAnimationFrame(animationId);
    document.getElementById('loopbackBtn').disabled=false;
    document.getElementById('stopLoopbackBtn').disabled=true;
    document.getElementById('volumeFill').style.width='0%';
}

function updateVolumeIndicator(){
    if(!loopbackActive||!analyserNode)return;
    const data=new Uint8Array(analyserNode.frequencyBinCount);
    analyserNode.getByteTimeDomainData(data);
    let max=0;
    for(let i=0;i<data.length;i++){
        const v=(data[i]-128)/128;
        max=Math.max(max,Math.abs(v));
    }
    document.getElementById('volumeFill').style.width=Math.min(max*100,100)+'%';
    animationId=requestAnimationFrame(updateVolumeIndicator);
}

async function startLiveVolumeIndicator(){
    const stream=await getAudioStream();
    if(!stream)return;
    const ctx=new AudioContext();
    const source=ctx.createMediaStreamSource(stream);
    liveAnalyser=ctx.createAnalyser();
    source.connect(liveAnalyser);
    function update(){
        if(!liveAnalyser)return;
        const data=new Uint8Array(liveAnalyser.frequencyBinCount);
        liveAnalyser.getByteTimeDomainData(data);
        let max=0;
        for(let i=0;i<data.length;i++){
            const v=(data[i]-128)/128;
            max=Math.max(max,Math.abs(v));
        }
        const p=Math.min(max*100,100);
        document.getElementById('liveVolumeFill').style.width=p+'%';
        const ad=document.getElementById('volumeAdvice');
        const ins=document.getElementById('volumeInstructions');
        if(p<10){ad.innerHTML='Too quiet. Increase mic gain.';ins.style.display='block';}
        else if(p>90){ad.innerHTML='Too loud. Decrease mic gain.';ins.style.display='block';}
        else{ad.innerHTML='Good level';ins.style.display='none';}
        liveAnimationId=requestAnimationFrame(update);
    }
    update();
}

function stopLiveVolumeIndicator(){
    if(liveAnimationId)cancelAnimationFrame(liveAnimationId);
    liveAnalyser=null;
}
async function startRecording(sec){
    const stream=await getAudioStream();
    if(!stream)return null;
    recordedChunks=[];
    mediaRecorder=new MediaRecorder(stream);
    mediaRecorder.ondataavailable=e=>{if(e.data.size>0)recordedChunks.push(e.data);};
    mediaRecorder.start();
    return new Promise(resolve=>{
        setTimeout(async()=>{
            mediaRecorder.stop();
            stream.getTracks().forEach(t=>t.stop());
            await new Promise(r=>setTimeout(r,100));
            const blob=new Blob(recordedChunks);
            const reader=new FileReader();
            reader.onloadend=()=>resolve(reader.result.split(',')[1]);
            reader.readAsDataURL(blob);
        },sec*1000);
    });
}

async function recordSilence(){
    const btn=document.getElementById('recordNoiseBtn');
    btn.disabled=true;
    btn.textContent='Recording...';
    try{
        const b64=await startRecording(3);
        const r=await fetch('/api/mictest/noise',{
            method:'POST',
            headers:{'Content-Type':'application/json'},
            body:JSON.stringify({audio_base64:b64})
        });
        const d=await r.json();
        document.getElementById('noiseResult').innerHTML='Noise: '+d.noise_db+' dB<br>'+d.advice';
        calibrationData.noise_db=d.noise_db;
        calibrationData.noise_level=d.level;
        calibrationData.noise_advice=d.advice;
        calibrationData.steps_completed.push(1);
    }catch(e){
        document.getElementById('noiseResult').innerHTML='Error measuring noise';
    }finally{
        btn.disabled=false;
        btn.textContent='Record 3 sec silence';
    }
}

async function recordTestPhrase(){
    const btn=document.getElementById('recordPhraseBtn');
    btn.disabled=true;
    btn.textContent='Recording...';
    try{
        const stream=await getAudioStream();
        if(!stream)return;
        recordedChunks=[];
        const recorder=new MediaRecorder(stream);
        recorder.ondataavailable=e=>{if(e.data.size>0)recordedChunks.push(e.data);};
        recorder.start();
        await new Promise(r=>setTimeout(r,5000));
        recorder.stop();
        stream.getTracks().forEach(t=>t.stop());
        await new Promise(r=>setTimeout(r,100));
        const blob=new Blob(recordedChunks);
        const b64=await new Promise(resolve=>{
            const reader=new FileReader();
            reader.onloadend=()=>resolve(reader.result.split(',')[1]);
            reader.readAsDataURL(blob);
        });
        const r=await fetch('/api/mictest/test_phrase',{
            method:'POST',
            headers:{'Content-Type':'application/json'},
            body:JSON.stringify({audio_base64:b64,expected_text:calibrationData.test_phrase_original})
        });
        const d=await r.json();
        document.getElementById('phraseResult').innerHTML='You said: "'+d.transcribed+'"<br>WER: '+d.wer+'%<br>'+d.advice;
        calibrationData.wer=d.wer;
        calibrationData.transcribed=d.transcribed;
        calibrationData.steps_completed.push(3);
    }catch(e){
        document.getElementById('phraseResult').innerHTML='Error recognizing speech';
    }finally{
        btn.disabled=false;
        btn.textContent='Record phrase';
    }
}

async function saveCalibration(){
    const btn=document.getElementById('saveBtn');
    btn.disabled=true;
    btn.textContent='Saving...';
    try{
        calibrationData.timestamp=new Date().toISOString();
        const r=await fetch('/api/mictest/save',{
            method:'POST',
            headers:{'Content-Type':'application/json'},
            body:JSON.stringify({profile_name:profileName,calibration:calibrationData})
        });
        const d=await r.json();
        document.getElementById('saveResult').innerHTML=d.status==='saved'?'Settings saved!':'Error saving';
    }catch(e){
        document.getElementById('saveResult').innerHTML='Error saving';
    }finally{
        btn.disabled=false;
        btn.textContent='Save settings';
    }
}

async function resetCalibration(){
    if(!confirm('Reset all microphone calibration settings?'))return;
    const btn=document.getElementById('resetBtn');
    btn.disabled=true;
    btn.textContent='Resetting...';
    try{
        const r=await fetch('/api/mictest/reset',{
            method:'POST',
            headers:{'Content-Type':'application/json'},
            body:JSON.stringify({profile_name:profileName})
        });
        const d=await r.json();
        document.getElementById('saveResult').innerHTML=d.status==='reset'?'Reset to default':'Error resetting';
        calibrationData={test_phrase_original:calibrationData.test_phrase_original,steps_completed:[]};
    }catch(e){
        document.getElementById('saveResult').innerHTML='Error resetting';
    }finally{
        btn.disabled=false;
        btn.textContent='Reset to default';
    }
}

function checkVolumeAgain(){
    const p=parseFloat(document.getElementById('liveVolumeFill').style.width)||0;
    const ad=document.getElementById('volumeAdvice');
    const ins=document.getElementById('volumeInstructions');
    if(p<10){
        ad.innerHTML='Still too quiet. Increase gain more.';
        ins.style.display='block';
    }else if(p>90){
        ad.innerHTML='Still too loud. Decrease gain.';
        ins.style.display='block';
    }else{
        ad.innerHTML='Perfect! Volume is optimal.';
        ins.style.display='none';
        calibrationData.steps_completed.push(2);
    }
}

function initEventHandlers(){
    document.getElementById('loopbackBtn').onclick=startLoopback;
    document.getElementById('stopLoopbackBtn').onclick=stopLoopback;
    document.getElementById('recordNoiseBtn').onclick=recordSilence;
    document.getElementById('recordPhraseBtn').onclick=recordTestPhrase;
    document.getElementById('saveBtn').onclick=saveCalibration;
    document.getElementById('resetBtn').onclick=resetCalibration;
    document.getElementById('closeBtn').onclick=()=>window.close();
    document.getElementById('checkVolumeBtn').onclick=checkVolumeAgain;
    document.querySelectorAll('.skip').forEach(btn=>{
        btn.onclick=()=>{
            const s=parseInt(btn.dataset.step);
            if(!calibrationData.steps_completed.includes(s))calibrationData.steps_completed.push(s);
            btn.style.opacity='0.5';
        };
    });
    const observer=new IntersectionObserver(entries=>{
        entries.forEach(entry=>{
            if(entry.isIntersecting)startLiveVolumeIndicator();
            else stopLiveVolumeIndicator();
        });
    });
    observer.observe(document.getElementById('step2'));
}

window.onload=async()=>{
    await loadProfileName();
    initEventHandlers();
};
window.onbeforeunload=()=>stopAllAudio();
