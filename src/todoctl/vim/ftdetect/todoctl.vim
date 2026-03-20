" src/todoctl/vim/ftdetect/todoctl.vim
augroup todoctl_filetype
    autocmd!
    autocmd BufRead,BufNewFile *.todo set filetype=todoctl
augroup END
