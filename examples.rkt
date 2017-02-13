;; invocation of set-name
;; it is its own inverse
(set-name #:labels labels
          #:target (interval #:index 3 #:name "a")
          #:new-name "b")

(set-name #:labels labels
          #:target (interval #:index 3 #:name "b")
          #:new-name "a")

;; invocation of set-boundary
;; it is its own inverse
(set-boundary #:labels labels
              #:target (interval #:index 3 #:bd 3.141)
              #:which "start"
              #:new-bd 3.131)

(set-boundary #:labels labels
              #:target (interval #:index 3 #:bd 3.131)
              #:which "start"
              #:new-bd 3.141)

;; invocation of merge-next and split
;; these are one another's inverses
(merge-next #:labels labels
            #:target (interval-pair #:index 3
                                    #:name "b"
                                    #:sep 3.240
                                    #:next-name "silence")
            #:new-name "q"
            #:new-sep null
            #:new-next-name null)

(split #:labels labels
       #:target (interval-pair #:index 3
                               #:name "q"
                               #:sep null
                               #:next-name null)
        #:new-name "b"
        #:new-sep 3.240
        #:new-next-name "silence")

;; invocation of delete and create
;; these are one another's inverses
(delete #:labels labels
        #:target (interval #:index 3 . args))

(create #:labels labels
        #:target (interval #:index 3 . args))