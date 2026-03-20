" src/todoctl/vim/syntax/todoctl.vim
if exists("b:current_syntax")
  finish
endif

syntax match todoctlHeader "^# todoctl month: .*$"
syntax match todoctlId "^\[[0-9]\+\]"
syntax match todoctlComment "^#.*$"

syntax match todoctlStatusOpen "\[OPEN\]"
syntax match todoctlStatusDoing "\[DOING\]"
syntax match todoctlStatusSide "\[SIDE\]"
syntax match todoctlStatusDone "\[DONE\]"

highlight default link todoctlHeader Title
highlight default link todoctlId Identifier
highlight default link todoctlComment Comment

highlight todoctlStatusOpen ctermfg=2 guifg=#98c379
highlight todoctlStatusDoing ctermfg=3 guifg=#e5c07b
highlight todoctlStatusSide ctermfg=4 guifg=#61afef
highlight todoctlStatusDone ctermfg=8 guifg=#7f848e

syntax match todoctlStatusOpen "\[OPEN\]" conceal cchar=○
syntax match todoctlStatusDoing "\[DOING\]" conceal cchar=▶
syntax match todoctlStatusSide "\[SIDE\]" conceal cchar=◆
syntax match todoctlStatusDone "\[DONE\]" conceal cchar=✔

let b:current_syntax = "todoctl"
