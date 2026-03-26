pipeline {
    agent any
    environment {
        EC2_USER       = 'ubuntu'
        EC2_IP         = branchIP()
        REMOTE_DIR     = "/home/ubuntu/projects/odoo_${env.BRANCH_NAME}"
        POSTGRES_DB    = "db_${env.BRANCH_NAME}"
        DB_PASS_CRED   = credentials('odoo-db-password')
    }

    stages {
        stage('Smart Unit Tests') {
            steps {
                script {
                    def commitMsg = sh(script: "git log -1 --pretty=%B", returnStdout: true).trim()
                    def targetModule = getTargetModule(commitMsg)
                    
                    if (targetModule) {
                        // TRUCO: Obtenemos el ID del contenedor de Jenkins para heredar sus volúmenes
                        def jenkinsID = sh(script: 'hostname', returnStdout: true).trim()
                        
                        withEnv(["DB_PASS=${DB_PASS_CRED}"]) {
                            sh """
                                docker network create test-net-${BUILD_NUMBER} || true
                                
                                docker run -d --name db-test-${BUILD_NUMBER} \
                                    --network test-net-${BUILD_NUMBER} \
                                    -e POSTGRES_PASSWORD=\$DB_PASS -e POSTGRES_USER=odoo -e POSTGRES_DB=postgres \
                                    postgres:16-alpine
                                
                                sleep 10

                                # Usamos --volumes-from para que Odoo vea exactamente lo mismo que Jenkins
                                docker run --rm --name odoo-test-${BUILD_NUMBER} \
                                    --network test-net-${BUILD_NUMBER} \
                                    --volumes-from ${jenkinsID} \
                                    --user root \
                                    odoo:19.0 sh -c "
                                        pip install --break-system-packages websocket-client && \
                                        odoo -d odoo_test \
                                        --db_host db-test-${BUILD_NUMBER} \
                                        --db_user odoo \
                                        --db_password=\$DB_PASS \
                                        --addons-path=${env.WORKSPACE}/addons \
                                        -i ${targetModule} --test-enable --stop-after-init --log-level=test --test-tags /${targetModule}
                                    "
                            """
                        }
                    }
                }
            }
            post {
                always {
                    sh "docker stop db-test-${BUILD_NUMBER} || true && docker rm db-test-${BUILD_NUMBER} || true"
                    sh "docker network rm test-net-${BUILD_NUMBER} || true"
                }
            }
        }

        stage('Deploy to EC2') {
            steps {
                sshagent(['ec2-odoo-key']) { 
                    withEnv(["DB_PASS=${DB_PASS_CRED}"]) {
                        sh """
                            ssh -o StrictHostKeyChecking=no ${EC2_USER}@${EC2_IP} "mkdir -p ${REMOTE_DIR}"
                            scp -r ./* ${EC2_USER}@${EC2_IP}:${REMOTE_DIR}
                            
                            ssh -o StrictHostKeyChecking=no ${EC2_USER}@${EC2_IP} << 'EOF'
                                cd ${REMOTE_DIR}
                                sed -i "s/^db_password =.*/db_password = \$DB_PASS/" ./config/odoo.conf
                                export POSTGRES_PASSWORD=\$DB_PASS
                                
                                docker compose down --remove-orphans
                                docker compose up -d
                                
                                echo "Esperando estabilidad de Odoo..."
                                sleep 15 # Damos tiempo extra para que el entrypoint termine
                                
                                # Verificación robusta: Solo procede si el status es 'running' y NO está reiniciando
                                STATUS=\$(docker inspect -f '{{.State.Status}}' \$(docker compose ps -q odoo))
                                if [ "\$STATUS" != "running" ]; then
                                    echo "ERROR: El contenedor está en estado \$STATUS. Revisa los logs con 'docker compose logs odoo'"
                                    exit 1
                                fi

                                docker compose exec -T odoo odoo -d ${POSTGRES_DB} -u all --stop-after-init --no-http
EOF
                        """
                    }
                }
            }
        }
    }
}

@NonCPS
def getTargetModule(String msg) {
    def match = (msg =~ /MOD:([a-zA-Z0-9_]+)/)
    return match ? match[0][1] : null
}

def branchIP() { 
    return (env.BRANCH_NAME == 'main') ? '3.144.231.64' : '18.219.33.101' 
}

def branchPort() { 
    return (env.BRANCH_NAME == 'main') ? '8071' : '8070' 
}