<template>
  <div class="ptz-joystick">
    <div class="ptz-pad">
      <button class="ptz-btn up" @click="pan(0, -8)" title="上">▲</button>
      <button class="ptz-btn left" @click="pan(-8, 0)" title="左">◀</button>
      <button class="ptz-btn center" @click="reset" title="复位">●</button>
      <button class="ptz-btn right" @click="pan(8, 0)" title="右">▶</button>
      <button class="ptz-btn down" @click="pan(0, 8)" title="下">▼</button>
    </div>
    <div class="ptz-hint">PTZ 云台</div>
  </div>
</template>

<script setup>
const emit = defineEmits(['pan', 'reset'])
function pan(dx, dy) { emit('pan', dx, dy) }
function reset() { emit('reset') }
</script>

<style scoped>
.ptz-joystick { position: absolute; bottom: 14px; right: 14px; z-index: 5; display: flex; flex-direction: column; align-items: center; gap: 4px; }
.ptz-pad { display: grid; grid-template-columns: repeat(3, 30px); grid-template-rows: repeat(3, 30px); gap: 2px; background: rgba(0,0,0,0.55); padding: 4px; border-radius: 8px; }
.ptz-btn { background: rgba(255,255,255,0.15); color: #fff; border: none; border-radius: 4px; cursor: pointer; font-size: 11px; line-height: 1; }
.ptz-btn:hover { background: rgba(255,255,255,0.35); }
.up { grid-column: 2; grid-row: 1; }
.left { grid-column: 1; grid-row: 2; }
.center { grid-column: 2; grid-row: 2; }
.right { grid-column: 3; grid-row: 2; }
.down { grid-column: 2; grid-row: 3; }
.ptz-hint { color: rgba(255,255,255,0.7); font-size: 10px; }
</style>
