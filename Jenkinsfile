//This jenkins file was created for a single node installation, so aware of hacks here and there

pipeline {
	agent none
	stages {
		stage('Basic syntax check') {
			agent {
				docker {
					image 'python:3.6.5-alpine3.7'
				}
			}
			steps {
				sh '''python3 -m py_compile galera_node_health/__init__.py
				      python3 -m py_compile galera_node_health/scripts.py
				      python3 -m py_compile tests/function_tests/test_main.py
				      python3 -m py_compile tests/image_tests/test_docker_image.py'''
			}
		}
		stage('Acceptance tests') {
			parallel {
				stage('MariaDB-10.2'){
					agent {
						docker {
							image 'galera-node-health_tests_mariadb_10_2:latest'
							args '-v /etc/passwd:/etc/passwd:ro'        // this is required so jenkins user exists in docker
						}
					}
					steps {
						sh 'jenkins/function_tests.sh'
					}
					post {
						always {
							junit "test-reports/${STAGE_NAME}.xml"
						}
					}

				}
				stage('Percona-Cluster-5.7'){
					agent {
						docker {
							image 'galera-node-health_tests_percona_5_7:latest'
							args '-v /etc/passwd:/etc/passwd:ro'
						}
					}
					steps {
						sh 'jenkins/function_tests.sh'
					}
					post {
						always {
							junit "test-reports/${STAGE_NAME}.xml"
						}
					}

				}
				stage('MySQL-5.7'){
					agent {
						docker {
							image 'galera-node-health_tests_mysql_5_7:latest'
							args '-v /etc/passwd:/etc/passwd:ro'
						}
					}
					steps {
						sh 'jenkins/function_tests.sh'
					}
					post {
						always {
							junit "test-reports/${STAGE_NAME}.xml"
						}
					}

				}
			}
		}
		stage('Build docker image') {
		    agent {
		        label 'docker_builder'
		    }
		    steps {
		        sh '''
		            DOCKER_VERSION=`cat "docker/Dockerfile" | grep '#VERSION' | awk '{print $2}'`
                    DOCKER_NAME=`echo "$DOCKER_VERSION" | cut -f1 -d ':'`
                    DOCKER_TAG=`echo "$DOCKER_VERSION" | cut -f2 -d ':'`
                    cd docker
                    ./build_script.sh --tag $DOCKER_NAME:$DOCKER_TAG .
                    docker tag $DOCKER_NAME:$DOCKER_TAG $DOCKER_NAME:latest
		        '''
		    }
		}
		stage('Test docker image') {
		    agent {
		        docker {
		            image 'galera-node-health_image_tests:latest'
		            label 'docker_builder'
		            args '-v /var/run/docker.sock:/var/run/docker.sock -v /tmp/tests_shared:/tmp/tests_shared -u 0'
		        }
		    }
		    steps {
		        sh 'jenkins/image_tests.sh'
		    }
		    post {
		        always {
                    junit "test-reports/${STAGE_NAME}.xml"
                    sh 'rm -rf test-reports .pytest_cache tests/image_tests/__pycache__ /tmp/tests_shared/* || echo "Could not remove everything..."'
		        }
		    }
		}
	}
}
