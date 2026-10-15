import { spawn, type ChildProcessWithoutNullStreams } from 'node:child_process';
import { app } from 'electron';
import { join } from 'node:path';
import { EventEmitter } from 'node:events';
export type HotkeyEvent={action:'ready'|'talk-start'|'talk-end'|'talk-cancel'|'toggle'|'shortcut-conflict'|'inserted'|'insert-failed'|'worker-error';target?:number;cancelled?:boolean;shortcut?:string;reason?:string};
export class HotkeyManager extends EventEmitter {
  private child:ChildProcessWithoutNullStreams|null=null;
  start(){if(process.platform!=='win32'||this.child)return;const script=join(app.getAppPath(),'worker','hotkeys.py');const exe=join(process.resourcesPath,'resources','worker','MyAssistHotkeys.exe');this.child=app.isPackaged?spawn(exe,[],{stdio:['pipe','pipe','pipe'],windowsHide:true}):spawn('python',[script],{stdio:['pipe','pipe','pipe'],windowsHide:true});this.child.on('error',error=>this.emit('event',{action:'worker-error',reason:error.message}));this.child.stdin.on('error',error=>this.emit('event',{action:'worker-error',reason:error.message}));this.child.stdin.write(JSON.stringify({talkVk:0x20,talkModifiers:[0x11,0x10],toggleVk:0x4d,toggleModifiers:[0x11,0x10],cancelVk:0x1b})+'\n');let pending='';this.child.stdout.setEncoding('utf8');this.child.stdout.on('data',(chunk:string)=>{pending+=chunk;const lines=pending.split(/\r?\n/);pending=lines.pop()??'';for(const line of lines){try{this.emit('event',JSON.parse(line) as HotkeyEvent)}catch{}}});this.child.stderr.on('data',(chunk:Buffer)=>{const message=chunk.toString().trim().slice(0,240);if(message)this.emit('event',{action:'worker-error',reason:message})});this.child.on('exit',code=>{this.emit('exit',code);this.child=null;if(code!==0&&code!==2&&code!==3)this.emit('event',{action:'worker-error',reason:`Hotkey worker exited (${code??'unknown'}).`})})}
  insertText(target:number,text:string):boolean{const child=this.child;if(!child||child.killed||child.stdin.destroyed)return false;try{return child.stdin.write(JSON.stringify({kind:'insert',target,text})+'\n')}catch{return false}}
  stop(){if(this.child){this.child.stdin.write('{"kind":"shutdown"}\n');this.child.kill();this.child=null}}
}
