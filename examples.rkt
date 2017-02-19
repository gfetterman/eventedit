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
(merge-next #:target (interval #:index 3
                               #:name "b"
                               #:stop 3.240
                               #:next-name "silence"
                               #:next-start 3.240
                               . args)
            #:new-stop null
            #:new-next-start null)

(split #:target (interval #:index 3
                          #:name "b"
                          #:stop null
                          #:next-name "silence"
                          #:next-start null
                          . args)
        #:new-stop 3.240
        #:new-next-start 3.240)

;; invocation of delete and create
;; these are one another's inverses
(delete #:target (interval #:index 3 . args))

(create #:target (interval #:index 3 . args))