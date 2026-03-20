" src/todoctl/vim/ftplugin/todoctl.vim
setlocal nowrap
setlocal nospell
setlocal commentstring=#\ %s
setlocal conceallevel=2

" Cycle todo status on current line
function! TodoctlCycleStatus()
  let l:line = getline('.')

  if l:line =~# '^\[[0-9]\+\] \[OPEN\] '
    call setline('.', substitute(l:line, '\[OPEN\]', '[DOING]', ''))
  elseif l:line =~# '^\[[0-9]\+\] \[DOING\] '
    call setline('.', substitute(l:line, '\[DOING\]', '[SIDE]', ''))
  elseif l:line =~# '^\[[0-9]\+\] \[SIDE\] '
    call setline('.', substitute(l:line, '\[SIDE\]', '[DONE]', ''))
  elseif l:line =~# '^\[[0-9]\+\] \[DONE\] '
    call setline('.', substitute(l:line, '\[DONE\]', '[OPEN]', ''))
  endif
endfunction

" Press 't' to cycle status
nnoremap <buffer> <silent> t :call TodoctlCycleStatus()<CR>

" Fold contiguous blocks with the same status
function! TodoctlFoldExpr()
  let l:line = getline(v:lnum)

  " Ignore header or empty lines
  if l:line =~# '^#' || l:line =~# '^\s*$'
    return 0
  endif

  " Match todo line
  if l:line =~# '^\[[0-9]\+\] \[[A-Z]\+\] '
    let l:status = matchstr(l:line, '\[\zs[A-Z]\+\ze\]')

    " First line always starts a fold
    if v:lnum == 1
      return '>1'
    endif

    let l:prev = getline(v:lnum - 1)

    if l:prev =~# '^\[[0-9]\+\] \[[A-Z]\+\] '
      let l:prev_status = matchstr(l:prev, '\[\zs[A-Z]\+\ze\]')
      if l:status ==# l:prev_status
        return 1
      endif
    endif

    return '>1'
  endif

  return 0
endfunction

setlocal foldmethod=expr
setlocal foldexpr=TodoctlFoldExpr()
setlocal foldlevel=99

" Toggle current fold
nnoremap <buffer> z za

" Close all folds
nnoremap <buffer> Z zM

" Open all folds
nnoremap <buffer> O zR
