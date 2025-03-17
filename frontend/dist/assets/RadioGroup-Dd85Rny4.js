import{S as ee,U as oe,ak as D,r as k,Q as F,aj as P,V,H as $,ax as B,G as _,ae as m,af as C,E as I,bl as T,d as te,I as A,hp as re,an as ne,b3 as ae,p as U,aQ as E,J as ie,bn as de,bp as se,K as G}from"./index-Bby_nErz.js";const fe={name:String,value:{type:[String,Number,Boolean],default:"on"},checked:{type:Boolean,default:void 0},defaultChecked:Boolean,disabled:{type:Boolean,default:void 0},label:String,size:String,onUpdateChecked:[Function,Array],"onUpdate:checked":[Function,Array],checkedValue:{type:Boolean,default:void 0}},j=ee("n-radio-group");function ve(e){const o=oe(j,null),r=D(e,{mergedSize(t){const{size:a}=e;if(a!==void 0)return a;if(o){const{mergedSizeRef:{value:d}}=o;if(d!==void 0)return d}return t?t.mergedSize.value:"medium"},mergedDisabled(t){return!!(e.disabled||o?.disabledRef.value||t?.disabled.value)}}),{mergedSizeRef:b,mergedDisabledRef:n}=r,s=k(null),l=k(null),u=k(e.defaultChecked),f=F(e,"checked"),g=P(f,u),h=V(()=>o?o.valueRef.value===e.value:g.value),R=V(()=>{const{name:t}=e;if(t!==void 0)return t;if(o)return o.nameRef.value}),v=k(!1);function x(){if(o){const{doUpdateValue:t}=o,{value:a}=e;B(t,a)}else{const{onUpdateChecked:t,"onUpdate:checked":a}=e,{nTriggerFormInput:d,nTriggerFormChange:i}=r;t&&B(t,!0),a&&B(a,!0),d(),i(),u.value=!0}}function p(){n.value||h.value||x()}function y(){p(),s.value&&(s.value.checked=h.value)}function z(){v.value=!1}function S(){v.value=!0}return{mergedClsPrefix:o?o.mergedClsPrefixRef:$(e).mergedClsPrefixRef,inputRef:s,labelRef:l,mergedName:R,mergedDisabled:n,renderSafeChecked:h,focus:v,mergedSize:b,handleRadioInputChange:y,handleRadioInputBlur:z,handleRadioInputFocus:S}}const le=_("radio-group",`
 display: inline-block;
 font-size: var(--n-font-size);
`,[m("splitor",`
 display: inline-block;
 vertical-align: bottom;
 width: 1px;
 transition:
 background-color .3s var(--n-bezier),
 opacity .3s var(--n-bezier);
 background: var(--n-button-border-color);
 `,[C("checked",{backgroundColor:"var(--n-button-border-color-active)"}),C("disabled",{opacity:"var(--n-opacity-disabled)"})]),C("button-group",`
 white-space: nowrap;
 height: var(--n-height);
 line-height: var(--n-height);
 `,[_("radio-button",{height:"var(--n-height)",lineHeight:"var(--n-height)"}),m("splitor",{height:"var(--n-height)"})]),_("radio-button",`
 vertical-align: bottom;
 outline: none;
 position: relative;
 user-select: none;
 -webkit-user-select: none;
 display: inline-block;
 box-sizing: border-box;
 padding-left: 14px;
 padding-right: 14px;
 white-space: nowrap;
 transition:
 background-color .3s var(--n-bezier),
 opacity .3s var(--n-bezier),
 border-color .3s var(--n-bezier),
 color .3s var(--n-bezier);
 background: var(--n-button-color);
 color: var(--n-button-text-color);
 border-top: 1px solid var(--n-button-border-color);
 border-bottom: 1px solid var(--n-button-border-color);
 `,[_("radio-input",`
 pointer-events: none;
 position: absolute;
 border: 0;
 border-radius: inherit;
 left: 0;
 right: 0;
 top: 0;
 bottom: 0;
 opacity: 0;
 z-index: 1;
 `),m("state-border",`
 z-index: 1;
 pointer-events: none;
 position: absolute;
 box-shadow: var(--n-button-box-shadow);
 transition: box-shadow .3s var(--n-bezier);
 left: -1px;
 bottom: -1px;
 right: -1px;
 top: -1px;
 `),I("&:first-child",`
 border-top-left-radius: var(--n-button-border-radius);
 border-bottom-left-radius: var(--n-button-border-radius);
 border-left: 1px solid var(--n-button-border-color);
 `,[m("state-border",`
 border-top-left-radius: var(--n-button-border-radius);
 border-bottom-left-radius: var(--n-button-border-radius);
 `)]),I("&:last-child",`
 border-top-right-radius: var(--n-button-border-radius);
 border-bottom-right-radius: var(--n-button-border-radius);
 border-right: 1px solid var(--n-button-border-color);
 `,[m("state-border",`
 border-top-right-radius: var(--n-button-border-radius);
 border-bottom-right-radius: var(--n-button-border-radius);
 `)]),T("disabled",`
 cursor: pointer;
 `,[I("&:hover",[m("state-border",`
 transition: box-shadow .3s var(--n-bezier);
 box-shadow: var(--n-button-box-shadow-hover);
 `),T("checked",{color:"var(--n-button-text-color-hover)"})]),C("focus",[I("&:not(:active)",[m("state-border",{boxShadow:"var(--n-button-box-shadow-focus)"})])])]),C("checked",`
 background: var(--n-button-color-active);
 color: var(--n-button-text-color-active);
 border-color: var(--n-button-border-color-active);
 `),C("disabled",`
 cursor: not-allowed;
 opacity: var(--n-opacity-disabled);
 `)])]);function ue(e,o,r){var b;const n=[];let s=!1;for(let l=0;l<e.length;++l){const u=e[l],f=(b=u.type)===null||b===void 0?void 0:b.name;f==="RadioButton"&&(s=!0);const g=u.props;if(f!=="RadioButton"){n.push(u);continue}if(l===0)n.push(u);else{const h=n[n.length-1].props,R=o===h.value,v=h.disabled,x=o===g.value,p=g.disabled,y=(R?2:0)+(v?0:1),z=(x?2:0)+(p?0:1),S={[`${r}-radio-group__splitor--disabled`]:v,[`${r}-radio-group__splitor--checked`]:R},t={[`${r}-radio-group__splitor--disabled`]:p,[`${r}-radio-group__splitor--checked`]:x},a=y<z?t:S;n.push(G("div",{class:[`${r}-radio-group__splitor`,a]}),u)}}return{children:n,isButtonGroup:s}}const ce=Object.assign(Object.assign({},A.props),{name:String,value:[String,Number,Boolean],defaultValue:{type:[String,Number,Boolean],default:null},size:String,disabled:{type:Boolean,default:void 0},"onUpdate:value":[Function,Array],onUpdateValue:[Function,Array]}),he=te({name:"RadioGroup",props:ce,setup(e){const o=k(null),{mergedSizeRef:r,mergedDisabledRef:b,nTriggerFormChange:n,nTriggerFormInput:s,nTriggerFormBlur:l,nTriggerFormFocus:u}=D(e),{mergedClsPrefixRef:f,inlineThemeDisabled:g,mergedRtlRef:h}=$(e),R=A("Radio","-radio-group",le,re,e,f),v=k(e.defaultValue),x=F(e,"value"),p=P(x,v);function y(i){const{onUpdateValue:c,"onUpdate:value":w}=e;c&&B(c,i),w&&B(w,i),v.value=i,n(),s()}function z(i){const{value:c}=o;c&&(c.contains(i.relatedTarget)||u())}function S(i){const{value:c}=o;c&&(c.contains(i.relatedTarget)||l())}ne(j,{mergedClsPrefixRef:f,nameRef:F(e,"name"),valueRef:p,disabledRef:b,mergedSizeRef:r,doUpdateValue:y});const t=ae("Radio",h,f),a=U(()=>{const{value:i}=r,{common:{cubicBezierEaseInOut:c},self:{buttonBorderColor:w,buttonBorderColorActive:H,buttonBorderRadius:K,buttonBoxShadow:M,buttonBoxShadowFocus:N,buttonBoxShadowHover:O,buttonColor:Q,buttonColorActive:J,buttonTextColor:L,buttonTextColorActive:q,buttonTextColorHover:W,opacityDisabled:X,[E("buttonHeight",i)]:Y,[E("fontSize",i)]:Z}}=R.value;return{"--n-font-size":Z,"--n-bezier":c,"--n-button-border-color":w,"--n-button-border-color-active":H,"--n-button-border-radius":K,"--n-button-box-shadow":M,"--n-button-box-shadow-focus":N,"--n-button-box-shadow-hover":O,"--n-button-color":Q,"--n-button-color-active":J,"--n-button-text-color":L,"--n-button-text-color-hover":W,"--n-button-text-color-active":q,"--n-height":Y,"--n-opacity-disabled":X}}),d=g?ie("radio-group",U(()=>r.value[0]),a,e):void 0;return{selfElRef:o,rtlEnabled:t,mergedClsPrefix:f,mergedValue:p,handleFocusout:S,handleFocusin:z,cssVars:g?void 0:a,themeClass:d?.themeClass,onRender:d?.onRender}},render(){var e;const{mergedValue:o,mergedClsPrefix:r,handleFocusin:b,handleFocusout:n}=this,{children:s,isButtonGroup:l}=ue(de(se(this)),o,r);return(e=this.onRender)===null||e===void 0||e.call(this),G("div",{onFocusin:b,onFocusout:n,ref:"selfElRef",class:[`${r}-radio-group`,this.rtlEnabled&&`${r}-radio-group--rtl`,this.themeClass,l&&`${r}-radio-group--button-group`],style:this.cssVars},s)}});export{he as _,fe as r,ve as s};
