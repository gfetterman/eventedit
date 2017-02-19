;; invocation of set-name
;; it is its own inverse
(set-name #:target (interval #:index 3 #:name "a")
          #:new-name "b")

(set-name #:target (interval #:index 3 #:name "b")
          #:new-name "a")

;; invocation of set-start and set-stop
;; they are their own inverses
(set-start #:target (interval #:index 3 #:start 3.141)
           #:new-start 3.131)

(set-start #:target (interval #:index 3 #:start 3.131)
           #:new-start 3.141)

(set-stop #:target (interval #:index 3 #:stop 3.400)
          #:new-stop 3.450)

(set-stop #:target (interval #:index 3 #:stop 3.450)
          #:new-stop 3.400)

;; invocation of merge-next and split
;; these are one another's inverses
(merge-next #:target (interval-pair #:index 3
                                    #:name "b"
                                    #:sep 3.240
                                    #:next-name "silence"
                                    . args)
            #:new-name "q"
            #:new-sep null
            #:new-next-name null
            . args)

(split #:target (interval-pair #:index 3
                               #:name "q"
                               #:sep null
                               #:next-name null
                               . args)
        #:new-name "b"
        #:new-sep 3.240
        #:new-next-name "silence"
        . args)

;; invocation of delete and create
;; these are one another's inverses
(delete #:target (interval #:index 3 . args))

(create #:target (interval #:index 3 . args))